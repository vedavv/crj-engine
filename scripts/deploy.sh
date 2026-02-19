#!/usr/bin/env bash
# CRJ Engine — Deploy to Cloud Run + Firebase Hosting
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID env var}"
REGION="asia-south1"
IMAGE="asia-south1-docker.pkg.dev/${PROJECT_ID}/crj-engine/crj-engine"
TAG="${1:-latest}"

echo "=== Building Docker image ==="
gcloud builds submit \
  --tag "${IMAGE}:${TAG}" \
  --timeout=1800 \
  --region="${REGION}" \
  --project="${PROJECT_ID}"

echo "=== Deploying to Cloud Run ==="
gcloud run deploy crj-engine \
  --image "${IMAGE}:${TAG}" \
  --region "${REGION}" \
  --platform managed \
  --memory 4Gi \
  --cpu 2 \
  --timeout 120 \
  --concurrency 4 \
  --min-instances 0 \
  --max-instances 10 \
  --cpu-boost \
  --set-env-vars "OMP_NUM_THREADS=2,MKL_NUM_THREADS=2" \
  --allow-unauthenticated \
  --port 8080 \
  --project="${PROJECT_ID}"

echo "=== Deploying Firebase Hosting ==="
firebase deploy --only hosting --project="${PROJECT_ID}"

CLOUD_RUN_URL=$(gcloud run services describe crj-engine \
  --region="${REGION}" --project="${PROJECT_ID}" \
  --format='value(status.url)')

echo ""
echo "=== Deployment complete ==="
echo "Cloud Run:        ${CLOUD_RUN_URL}"
echo "Firebase Hosting: https://${PROJECT_ID}.web.app"
