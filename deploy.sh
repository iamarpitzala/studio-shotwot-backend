#!/usr/bin/env bash
# deploy.sh — Build and deploy the ShotWot backend to Cloud Run
#
# Prerequisites:
#   gcloud auth login && gcloud auth configure-docker asia-south1-docker.pkg.dev
#   gcloud services enable run.googleapis.com artifactregistry.googleapis.com
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-asia-south1}"
SERVICE_NAME="shotwot-backend"
REPO="shotwot"          # Artifact Registry repository name
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE_NAME}"

# The service account that the Cloud Run service will run as.
# It needs: Firestore User, Storage Object Admin, Vertex AI User, Firebase Auth roles.
SA_EMAIL="${SA_EMAIL:-shotwot-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com}"
# ──────────────────────────────────────────────────────────────────────────────

echo "▶ Building image: ${IMAGE}"
gcloud builds submit \
  --project="${PROJECT_ID}" \
  --tag="${IMAGE}" \
  .

echo "▶ Deploying to Cloud Run: ${SERVICE_NAME} in ${REGION}"
gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE}" \
  --platform=managed \
  --service-account="${SA_EMAIL}" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=300 \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars="GCP_REGION=${REGION}" \
  --set-env-vars="GCS_VAULT_BUCKET=${GCS_VAULT_BUCKET:-shotwot-brand-vault-poc}" \
  --set-env-vars="GCS_OUTPUT_BUCKET=${GCS_OUTPUT_BUCKET:-shotwot-generated-outputs-poc}" \
  --set-env-vars="FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-${PROJECT_ID}}" \
  --set-env-vars="ENVIRONMENT=production"

echo "✅ Backend deployed."
gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format="value(status.url)"
