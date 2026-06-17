# Backend — FastAPI + ML pipeline
FROM python:3.11-slim

WORKDIR /app

# System deps for scikit-learn / pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline source + ML models
COPY pipeline/ .
COPY data/ /app/data/

# Copy .env.example as fallback (Railway injects real env vars)
COPY .env.example /app/.env.example

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
