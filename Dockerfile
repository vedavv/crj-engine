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

# Install CPU-only PyTorch first (saves ~4.5 GB vs full CUDA build)
RUN pip install --no-cache-dir --prefix=/install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch torchcrepe torchaudio

# Copy project files and install
COPY pyproject.toml ./
COPY src/ ./src/
COPY configs/ ./configs/
RUN touch README.md && pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime — lean image
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY src/ ./src/
COPY configs/ ./configs/
COPY web/ ./web/

# Cloud Run injects PORT (default 8080)
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=2
ENV MKL_NUM_THREADS=2

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn crj_engine.api.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-keep-alive 120"]
