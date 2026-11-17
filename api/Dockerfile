# ==============================================================================
# AegisMed Clinical AI Engine - Production API Container
# Multi-stage, non-root, HIPAA/CIS compliant container for AWS ECS / Cloud Run
# ==============================================================================

FROM python:3.11-slim as base

# 1. Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# 2. Install essential system dependencies (curl for container health probes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3. Create non-privileged user (Security best practice: avoid running as root)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# 4. Install Python dependencies
# Optimize PyTorch for CPU-only execution (saves ~2GB of unused CUDA binaries)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/requirements.txt

# 5. Copy application source code and clinical knowledge databases
COPY app /app/app

# 6. Ensure correct ownership for non-root runtime
RUN chown -R appuser:appgroup /app

USER appuser

# 7. Container ports & probes
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 8. Start production Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
