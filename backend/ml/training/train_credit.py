import pandas as pd
import numpy as np
from pathlib import Path
import mlflow
import mlflow.sklearn
from sklearn.preprocessing import OrdinalEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score, f1_score, precision_score, recall_score, accuracy_score
import xgboost as xgb
import shap
import matplotlib.pyplot as plt
import optuna
import warnings

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

def print_metrics(y_true, y_pred, y_pred_proba, dataset_name):
    roc_auc = roc_auc_score(y_true, y_pred_proba)
    pr_auc = average_precision_score(y_true, y_pred_proba)
    f1 = f1_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    acc = accuracy_score(y_true, y_pred)
    
    print(f"\n{dataset_name} Metrics:")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"PR-AUC:    {pr_auc:.4f}")
    print(f"Accuracy:  {acc:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    
    return {"roc_auc": roc_auc, "pr_auc": pr_auc, "f1": f1, "precision": prec, "recall": rec, "accuracy": acc}

def main():
    print("Starting Credit Risk Model Training...")
    base_dir = Path(__file__).parent.parent.parent
    processed_dir = base_dir / "ml" / "data" / "processed"
    
    # MLflow Setup
    mlruns_path = base_dir / "mlruns" / "mlflow.db"
    mlruns_path.parent.mkdir(parents=True, exist_ok=True)
    
    tracking_uri = f"sqlite:///{mlruns_path.as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("loansense-credit-risk")
    
    # 1. Load data
    print("Loading datasets...")
    train_df = pd.read_parquet(processed_dir / "train.parquet")
    val_df = pd.read_parquet(processed_dir / "val.parquet")
    
    # 2. Define features
    features = [
        'income', 'loan_amount', 'emi_to_income_ratio', 'employment_type', 
        'cibil_score_simulated', 'loan_tenure_months', 'existing_obligations', 
        'account_age_months', 'new_to_credit'
    ]
    target = 'default_flag'
    
    X_train = train_df[features]
    y_train = train_df[target]
    
    X_val = val_df[features]
    y_val = val_df[target]
    
    # Calculate scale_pos_weight
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0
    print(f"Computed scale_pos_weight: {scale_pos_weight:.2f}")

    categorical_features = ['employment_type']
    categorical_transformer = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='passthrough'
    )
    
    # 3. Optuna Hyperparameter Tuning
    print("\nStarting Optuna Hyperparameter Tuning (Optimising for PR-AUC)...")
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 200),
            'max_depth': trial.suggest_int('max_depth', 3, 5),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 10, 50),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True),
            'scale_pos_weight': scale_pos_weight,
            'random_state': 42,
            'eval_metric': 'logloss'
        }
        
        clf = xgb.XGBClassifier(**params)
        
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', clf)
        ])
        
        pipeline.fit(X_train, y_train)
        y_val_pred_proba = pipeline.predict_proba(X_val)[:, 1]
        
        pr_auc = average_precision_score(y_val, y_val_pred_proba)
        return pr_auc

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=10)
    
    print(f"\nBest PR-AUC from tuning: {study.best_value:.4f}")
    print("Best Parameters:")
    for key, value in study.best_params.items():
        print(f"  {key}: {value}")
        
    best_params = study.best_params
    best_params['scale_pos_weight'] = scale_pos_weight
    best_params['random_state'] = 42
    best_params['eval_metric'] = 'logloss'
    
    # 4. Train Final Model & Log
    print("\nTraining Final Model with Best Parameters...")
    clf_final = xgb.XGBClassifier(**best_params)
    final_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', clf_final)
    ])
    
    with mlflow.start_run():
        mlflow.set_tags({"dataset_version": "v1", "feature_set": "credit_v1_tuned", "note": "fixed-label-feature-independence"})
        mlflow.log_params(best_params)
        
        final_pipeline.fit(X_train, y_train)
        
        # Training Metrics
        y_train_pred_proba = final_pipeline.predict_proba(X_train)[:, 1]
        y_train_pred = (y_train_pred_proba >= 0.5).astype(int)
        train_metrics = print_metrics(y_train, y_train_pred, y_train_pred_proba, "Training")
        
        # Validation Metrics
        y_val_pred_proba = final_pipeline.predict_proba(X_val)[:, 1]
        y_val_pred = (y_val_pred_proba >= 0.5).astype(int)
        val_metrics = print_metrics(y_val, y_val_pred, y_val_pred_proba, "Validation")
        
        # Log validation metrics
        mlflow_metrics = {f"val_{k}": v for k, v in val_metrics.items()}
        mlflow_metrics.update({f"train_{k}": v for k, v in train_metrics.items()})
        mlflow.log_metrics(mlflow_metrics)
        
        # Risk Bands Demonstration
        low_risk = (y_val_pred_proba < 0.3).sum()
        med_risk = ((y_val_pred_proba >= 0.3) & (y_val_pred_proba <= 0.6)).sum()
        high_risk = (y_val_pred_proba > 0.6).sum()
        print("\nValidation Set Risk Bands:")
        print(f"Low Risk (< 0.3): {low_risk} applicants")
        print(f"Medium Risk (0.3-0.6): {med_risk} applicants")
        print(f"High Risk (> 0.6): {high_risk} applicants")
        
        # Feature Importance (SHAP)
        print("\nGenerating SHAP feature importance plot...")
        X_train_transformed = final_pipeline.named_steps['preprocessor'].transform(X_train)
        
        cat_names = final_pipeline.named_steps['preprocessor'].transformers_[0][1].get_feature_names_out(categorical_features)
        num_names = [col for col in features if col not in categorical_features]
        all_feature_names = list(cat_names) + num_names
        
        X_train_transformed_df = pd.DataFrame(X_train_transformed, columns=all_feature_names).astype(float)
        
        explainer = shap.TreeExplainer(final_pipeline.named_steps['classifier'])
        shap_sample = X_train_transformed_df.sample(5000, random_state=42)
        shap_values = explainer.shap_values(shap_sample)
        
        plt.figure()
        shap.summary_plot(shap_values, shap_sample, show=False)
        shap_plot_path = base_dir / "ml" / "training" / "shap_summary_credit.png"
        shap_plot_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(shap_plot_path, bbox_inches='tight')
        mlflow.log_artifact(str(shap_plot_path))
        
        print("\n=== Baseline vs New Model Comparison ===")
        print(f"Metric       | Baseline (v6) | New Model")
        print(f"-------------|---------------|----------")
        print(f"ROC-AUC      | 0.6702        | {val_metrics['roc_auc']:.4f}")
        print(f"PR-AUC       | 0.3199        | {val_metrics['pr_auc']:.4f}")
        print(f"F1-Score     | 0.2829        | {val_metrics['f1']:.4f}")
        
        # Register Model
        print("\nLogging and Registering Model...")
        mlflow.sklearn.log_model(
            sk_model=final_pipeline,
            name="model",
            registered_model_name="credit-risk-scorer"
        )
        
        print("Done!")

if __name__ == "__main__":
    main()
