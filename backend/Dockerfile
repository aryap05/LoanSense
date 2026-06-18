FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT=8000

# Install dependencies needed for SQLite and standard build tools
RUN apt-get update && apt-get install -y gcc sqlite3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend
COPY . .

# Run the patch script to rewrite absolute Windows paths in MLflow SQLite database
RUN python scripts/patch_mlflow_paths.py

# Expose port
EXPOSE 8000

# Start command uses shell execution format to dynamically bind the injected PORT variable
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
