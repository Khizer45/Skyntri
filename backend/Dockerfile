# Skyntri API - production image (SK-05, SK-06, SK-11)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    ENVIRONMENT=production \
    AUTO_MIGRATE=false \
    UPLOAD_DIR=/data/uploads \
    MODEL_WARMUP=true

# Tesseract OCR binary (pytesseract is only a wrapper) + minimal libs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY models ./models
COPY docker-entrypoint.sh ./

# Non-root user; private upload volume.
RUN useradd --create-home --uid 10001 skyntri \
    && mkdir -p /data/uploads \
    && chown -R skyntri:skyntri /data /app \
    && chmod +x docker-entrypoint.sh

USER skyntri

VOLUME ["/data/uploads"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
# One worker: each worker loads its own TensorFlow model copy. Scale out
# with more containers after measuring memory (see docs/DEPLOYMENT_RUNBOOK.md).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
