import pandas as pd
import numpy as np
from pathlib import Path
import mlflow
import mlflow.sklearn
import mlflow.pyfunc
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OrdinalEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
from sklearn.base import clone
import joblib
import warnings
import sys
import os

# Add backend directory to path so we can import ml.training.contradiction.rules
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_path not in sys.path:
    sys.path.append(backend_path)
    
from ml.training.contradiction.rules import ContradictionRuleEngine

warnings.filterwarnings('ignore')

class ContradictionDetectorPyFunc(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        import joblib
        
        from ml.training.contradiction.rules import ContradictionRuleEngine
        
        
        self.isolation_forest = joblib.load(context.artifacts["isolation_forest"])
        self.logistic_regression = joblib.load(context.artifacts["logistic_regression"])
        self.rule_engine = ContradictionRuleEngine()
        
    def predict(self, context, model_input: pd.DataFrame):
        # model_input contains raw features + 'credit_risk_score' + 'fraud_probability'
        
        # 1. Compute anomaly score
        anomaly_features = model_input[self.isolation_forest.feature_names_in_]
        anomaly_score = -self.isolation_forest.score_samples(anomaly_features)
        
        # 2. Compute rules
        rule_counts = []
        any_high_severities = []
        contradiction_types = []
        rule_flags_list = []
        
        for _, row in model_input.iterrows():
            row_dict = row.to_dict()
            crs = row['credit_risk_score']
            fp = row['fraud_probability']
            
            rule_out = self.rule_engine.check(row_dict, crs, fp)
            rule_counts.append(rule_out['rule_flag_count'])
            any_high_severities.append(int(rule_out['any_high_severity']))
            
            # Determine contradiction type
            if rule_out['any_high_severity']:
                ctype = "UNKNOWN"
                for flag in rule_out['rule_flags']:
                    if flag['severity'] == 'HIGH':
                        ctype = flag['flag'].upper()
                        break
                contradiction_types.append(ctype)
            elif rule_out['rule_flag_count'] > 0:
                contradiction_types.append(rule_out['rule_flags'][0]['flag'].upper())
            else:
                contradiction_types.append("NONE")
            
            rule_flags_list.append(rule_out['rule_flags'])
            
        # 3. Meta model prediction
        meta_features = pd.DataFrame({
            'credit_risk_score': model_input['credit_risk_score'],
            'fraud_probability': model_input['fraud_probability'],
            'anomaly_score': anomaly_score,
            'rule_flag_count': rule_counts,
            'any_high_severity': any_high_severities
        })
        
        contradiction_scores = self.logistic_regression.predict_proba(meta_features)[:, 1]
        
        # 4. Finalise contradiction_type with anomaly fallback
        for i in range(len(contradiction_types)):
            if contradiction_types[i] == "NONE" and anomaly_score[i] > 0.7:
                contradiction_types[i] = "SIGNAL_DIVERGENCE"
        
        return pd.DataFrame({
            'contradiction_score': contradiction_scores,
            'anomaly_score': anomaly_score,
            'contradiction_type': contradiction_types,
            'rule_flags': rule_flags_list
        })


def evaluate_attacks(pyfunc_model, df_attacks, base_credit_model, base_fraud_model, credit_features, fraud_features):
    print("\n=== Attack Pattern Detection Rate (Contradiction > 0.6) ===")
    
    X_attacks_credit = df_attacks[credit_features]
    X_attacks_fraud = df_attacks[fraud_features]
    
    df_attacks['credit_risk_score'] = base_credit_model.predict_proba(X_attacks_credit)[:, 1]
    df_attacks['fraud_probability'] = base_fraud_model.predict_proba(X_attacks_fraud)[:, 1]
    
    output_df = pyfunc_model.predict(None, df_attacks)
    df_attacks['contradiction_score'] = output_df['contradiction_score']
    
    for pattern in df_attacks['pattern_label'].unique():
        df_pat = df_attacks[df_attacks['pattern_label'] == pattern]
        caught_count = (df_pat['contradiction_score'] > 0.6).sum()
        print(f"Pattern {pattern:35s}: {caught_count}/{len(df_pat)} ({(caught_count/len(df_pat))*100:.1f}%) caught")


def main():
    print("Starting Contradiction Detector Training (True OOF Stacking)...")
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    
    # MLflow Setup
    mlruns_path = base_dir / "mlruns" / "mlflow.db"
    tracking_uri = f"sqlite:///{mlruns_path.as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("loansense-contradiction")
    
    # 1. Load Data
    print("Loading datasets...")
    df_train = pd.read_parquet(processed_dir / "train.parquet")
    df_val = pd.read_parquet(processed_dir / "val.parquet")
    attacks_path = base_dir / "ml" / "data" / "attacks" / "combined_attacks.parquet"
    df_attacks = pd.read_parquet(attacks_path) if attacks_path.exists() else None
    
    for df in [df_train, df_val]:
        if 'new_to_credit' in df.columns and df['new_to_credit'].dtype == bool:
            df['new_to_credit'] = df['new_to_credit'].astype(int)
    if df_attacks is not None and df_attacks['new_to_credit'].dtype == bool:
        df_attacks['new_to_credit'] = df_attacks['new_to_credit'].astype(int)
    
    credit_features = [
        'income', 'loan_amount', 'emi_to_income_ratio', 'employment_type', 
        'cibil_score_simulated', 'loan_tenure_months', 'existing_obligations', 
        'account_age_months', 'new_to_credit'
    ]
    fraud_features = [
        'transaction_velocity_30d', 'account_age_months', 'enquiry_count_30d', 
        'income_transaction_ratio', 'upi_velocity_percentile', 'new_to_credit', 'loan_amount'
    ]
    combined_features = list(set(credit_features + fraud_features))
    
    # 2. Load Base Models from MLflow
    print("Loading registered base models from MLflow...")
    base_credit_model = mlflow.sklearn.load_model("models:/credit-risk-scorer/latest")
    base_fraud_model = mlflow.sklearn.load_model("models:/fraud-signal-detector/latest")
    
    # 3. K-Fold OOF Scoring
    print("Generating Out-Of-Fold (OOF) scores for training data (K=5)...")
    oof_credit_score = np.zeros(len(df_train))
    oof_fraud_prob = np.zeros(len(df_train))
    oof_anomaly_score = np.zeros(len(df_train))
    
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(df_train, df_train['fraud_flag'])):
        print(f"  Processing Fold {fold + 1}/5...")
        fold_train = df_train.iloc[train_idx]
        fold_val = df_train.iloc[val_idx]
        
        # Credit Model OOF
        clone_credit = clone(base_credit_model)
        clone_credit.fit(fold_train[credit_features], fold_train['default_flag'])
        oof_credit_score[val_idx] = clone_credit.predict_proba(fold_val[credit_features])[:, 1]
        
        # Fraud Model OOF
        clone_fraud = clone(base_fraud_model)
        clone_fraud.fit(fold_train[fraud_features], fold_train['fraud_flag'])
        oof_fraud_prob[val_idx] = clone_fraud.predict_proba(fold_val[fraud_features])[:, 1]
        
        # Isolation Forest OOF
        preprocessor = ColumnTransformer(
            transformers=[('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), ['employment_type'])],
            remainder='passthrough'
        )
        iso_forest = Pipeline([
            ('preprocessor', preprocessor),
            ('iforest', IsolationForest(contamination=0.05, random_state=42))
        ])
        legit_train = fold_train[fold_train['fraud_flag'] == 0]
        iso_forest.fit(legit_train[combined_features])
        oof_anomaly_score[val_idx] = -iso_forest.score_samples(fold_val[combined_features])
    
    df_train['credit_risk_score'] = oof_credit_score
    df_train['fraud_probability'] = oof_fraud_prob
    df_train['anomaly_score'] = oof_anomaly_score
    
    # 4. Rule Engine Execution on Train Data
    print("Executing Rule Engine on OOF data...")
    rule_engine = ContradictionRuleEngine()
    rule_counts = []
    any_high = []
    
    for _, row in df_train.iterrows():
        out = rule_engine.check(row.to_dict(), row['credit_risk_score'], row['fraud_probability'])
        rule_counts.append(out['rule_flag_count'])
        any_high.append(int(out['any_high_severity']))
        
    df_train['rule_flag_count'] = rule_counts
    df_train['any_high_severity'] = any_high
    
    # 5. Train Meta-Model & Final Isolation Forest
    print("Training Final Logistic Regression Meta-Model...")
    meta_features = ['credit_risk_score', 'fraud_probability', 'anomaly_score', 'rule_flag_count', 'any_high_severity']
    
    meta_model = LogisticRegression(class_weight='balanced', random_state=42)
    meta_model.fit(df_train[meta_features], df_train['fraud_flag'])
    
    print("Training Final Isolation Forest on full legitimate training set...")
    preprocessor = ColumnTransformer(
        transformers=[('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), ['employment_type'])],
        remainder='passthrough'
    )
    final_iso_forest = Pipeline([
        ('preprocessor', preprocessor),
        ('iforest', IsolationForest(contamination=0.05, random_state=42))
    ])
    legit_full_train = df_train[df_train['fraud_flag'] == 0]
    final_iso_forest.fit(legit_full_train[combined_features])
    
    # 6. Evaluation on Val Set
    print("\nEvaluating on Validation Set...")
    df_val['credit_risk_score'] = base_credit_model.predict_proba(df_val[credit_features])[:, 1]
    df_val['fraud_probability'] = base_fraud_model.predict_proba(df_val[fraud_features])[:, 1]
    df_val['anomaly_score'] = -final_iso_forest.score_samples(df_val[combined_features])
    
    val_rule_counts = []
    val_any_high = []
    for _, row in df_val.iterrows():
        out = rule_engine.check(row.to_dict(), row['credit_risk_score'], row['fraud_probability'])
        val_rule_counts.append(out['rule_flag_count'])
        val_any_high.append(int(out['any_high_severity']))
        
    df_val['rule_flag_count'] = val_rule_counts
    df_val['any_high_severity'] = val_any_high
    
    val_preds_proba = meta_model.predict_proba(df_val[meta_features])[:, 1]
    val_auc = roc_auc_score(df_val['fraud_flag'], val_preds_proba)
    print(f"Validation Contradiction ROC-AUC: {val_auc:.4f}")
    
    # 7. MLflow Logging and Registration
    with mlflow.start_run():
        mlflow.log_param("meta_model", "LogisticRegression")
        mlflow.log_param("anomaly_model", "IsolationForest")
        mlflow.log_metric("val_roc_auc", val_auc)
        
        artifacts_dir = base_dir / "ml" / "training" / "tmp_artifacts"
        artifacts_dir.mkdir(exist_ok=True, parents=True)
        iso_path = artifacts_dir / "isolation_forest.pkl"
        lr_path = artifacts_dir / "logistic_regression.pkl"
        
        joblib.dump(final_iso_forest, iso_path)
        joblib.dump(meta_model, lr_path)
        
        artifacts = {
            "isolation_forest": str(iso_path),
            "logistic_regression": str(lr_path)
        }
        
        pyfunc_model_instance = ContradictionDetectorPyFunc()
        
        if df_attacks is not None:
            class MockContext:
                def __init__(self, artifacts):
                    self.artifacts = artifacts
            pyfunc_model_instance.load_context(MockContext(artifacts))
            evaluate_attacks(pyfunc_model_instance, df_attacks, base_credit_model, base_fraud_model, credit_features, fraud_features)
            
        print("\nLogging and Registering Custom PyFunc Model...")
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=ContradictionDetectorPyFunc(),
            artifacts=artifacts,
            registered_model_name="contradiction-detector"
        )
        print("Done!")

if __name__ == "__main__":
    main()
