$ErrorActionPreference = "Stop"
Write-Host "Running feature_engineering.py..."
d:\LoanSense\backend\.venv\Scripts\python.exe backend\ml\data\feature_engineering.py

Write-Host "`nRunning synthetic_layer.py..."
d:\LoanSense\backend\.venv\Scripts\python.exe backend\ml\data\synthetic_layer.py

Write-Host "`nRunning generate_attacks.py..."
d:\LoanSense\backend\.venv\Scripts\python.exe backend\ml\attack_generator\generate_attacks.py

Write-Host "`nRunning prepare_dataset.py..."
d:\LoanSense\backend\.venv\Scripts\python.exe backend\ml\data\prepare_dataset.py

Write-Host "`nRunning run_fraud_leakage_diagnostic.py..."
d:\LoanSense\backend\.venv\Scripts\python.exe backend\ml\data\run_fraud_leakage_diagnostic.py
