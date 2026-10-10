FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OMP_THREAD_LIMIT=1 OPENBLAS_NUM_THREADS=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
COPY apps/api/pyproject.toml /app/apps/api/pyproject.toml
COPY apps/api/src /app/apps/api/src
RUN pip install -e './apps/api[hosted-ingestion]' && useradd --create-home appuser \
    && mkdir -p /app/data/private/ingest && chown -R appuser:appuser /app/data
USER appuser
ENV INGESTION_ENABLED=true ORIGINAL_STORAGE=supabase OCR_ENGINE=tesseract
CMD ["sh", "-c", "exec uvicorn ps01_api.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
