# Render / cloud deploy — build context MUST be repo root (.)
# Optimized for low RAM: CPU-only PyTorch, GCN-only inference by default.

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app/backend \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    LOAD_GAT=false \
    LOAD_RF=false \
    LIVE_SIMULATOR_SAMPLE_ROWS=5000 \
    LIVE_SIMULATOR_INTERVAL_SECONDS=2 \
    LIVE_SIMULATOR_TICKS_PER_INTERVAL=5 \
    LIVE_SIMULATOR_ATTACKS_PER_10=4

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir "numpy>=1.26.4,<2.0.0" \
    && pip install --no-cache-dir "torch==2.1.2+cpu" --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
        pyg-lib torch-scatter torch-sparse torch-cluster torch-spline-conv \
        -f https://data.pyg.org/whl/torch-2.1.0+cpu.html \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-prod.txt /tmp/requirements-prod.txt
RUN pip install --no-cache-dir -r /tmp/requirements-prod.txt

COPY src /app/src
COPY artifacts/models /app/artifacts/models
COPY artifacts/data /app/artifacts/data
COPY backend /app/backend

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir /app/backend --workers 1"]
