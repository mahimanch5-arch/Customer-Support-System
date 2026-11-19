FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# App code + data (KB/DB) — the DB is read via SQLAlchemy; swap DATABASE_URL for Postgres in prod.
COPY pyproject.toml README.md ./
COPY app ./app
COPY _DB ./_DB
COPY _KB ./_KB

# Install the project's runtime dependencies (dev group excluded).
RUN pip install --no-cache-dir .

EXPOSE 8000

# Non-root runtime.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
