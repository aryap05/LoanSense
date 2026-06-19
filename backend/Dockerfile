FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Install dependencies needed for SQLite and standard build tools
RUN apt-get update && apt-get install -y gcc sqlite3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend
COPY backend/ .

# Copy the models (run directories 1, 2, 3) from the root mlruns
COPY mlruns/1/ ./mlruns/1/
COPY mlruns/2/ ./mlruns/2/
COPY mlruns/3/ ./mlruns/3/
COPY mlruns/mlflow.db ./mlruns/mlflow.db

# Run the patch script to rewrite absolute Windows paths in MLflow SQLite database
RUN python scripts/patch_mlflow_paths.py

# Expose port
EXPOSE 8000

# Start command uses shell execution format with exec to dynamically bind PORT and forward signals
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

