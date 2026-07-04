FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
COPY requirements.txt /app/requirements-ml.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt -r /app/requirements-ml.txt

COPY src /app/src
COPY artifacts/models /app/artifacts/models
COPY backend /app/backend

ENV PYTHONPATH=/app/src:/app/backend
ENV JWT_SECRET=change-me-in-production

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir /app/backend"]
