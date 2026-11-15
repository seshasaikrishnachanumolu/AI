FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    TF_ENABLE_ONEDNN_OPTS=0

WORKDIR /app

# libglib is required by OpenCV; the CPU-only TensorFlow build keeps the image smaller.
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN sed 's/^tensorflow/tensorflow-cpu/' requirements.txt > requirements.docker.txt \
    && pip install -r requirements.docker.txt

COPY . .

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/uploads /app/logs /app/instance \
    && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status == 200 else 1)"

# seed.py is idempotent: it creates tables, the admin user, locations and bins only if missing.
CMD ["sh", "-c", "python seed.py && python serve.py"]
