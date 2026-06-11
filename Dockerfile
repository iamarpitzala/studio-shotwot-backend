# ---- Build stage ----
FROM python:3.12-slim AS base

# Don't buffer stdout/stderr — important for Cloud Run logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# ---- Runtime ----
# Cloud Run injects $PORT at startup; default to 8080 (Cloud Run convention)
ENV PORT=8080

# Use exec form so signals reach uvicorn (graceful shutdown)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
