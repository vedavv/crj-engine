# ============================================================
# CRJ Engine — Multi-stage Docker build for Cloud Run
# ============================================================

# Stage 1: Builder — install Python dependencies
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install CPU-only PyTorch + all dependencies (no project install — use PYTHONPATH)
COPY pyproject.toml ./
COPY src/ ./src/
COPY configs/ ./configs/
RUN touch README.md && pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    .

# Stage 2: Runtime — lean image
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages and binaries (uvicorn, etc.) from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source tree (configs path resolution uses __file__ relative paths)
WORKDIR /app
COPY src/ ./src/
COPY configs/ ./configs/
COPY web/ ./web/

# Cloud Run injects PORT (default 8080)
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV OMP_NUM_THREADS=2
ENV MKL_NUM_THREADS=2

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn crj_engine.api.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-keep-alive 120"]
