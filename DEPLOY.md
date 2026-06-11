# ShotWot Backend — Cloud Run Deployment

## One-time setup

### 1. Enable GCP APIs
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com \
  --project=YOUR_PROJECT_ID
```

### 2. Create an Artifact Registry repository
```bash
gcloud artifacts repositories create shotwot \
  --repository-format=docker \
  --location=asia-south1 \
  --project=YOUR_PROJECT_ID
```

### 3. Create a dedicated service account for the backend
```bash
gcloud iam service-accounts create shotwot-backend-sa \
  --display-name="ShotWot Backend SA" \
  --project=YOUR_PROJECT_ID
```

Grant it the roles it needs:
```bash
SA="shotwot-backend-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com"
PROJECT="YOUR_PROJECT_ID"

# Firestore
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" --role="roles/datastore.user"

# GCS (read vault bucket, write output bucket)
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" --role="roles/storage.objectAdmin"

# Vertex AI (Gemini calls)
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" --role="roles/aiplatform.user"

# Firebase Auth token verification
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" --role="roles/firebase.sdkAdminServiceAgent"

# Allow the SA to sign blobs (needed for GCS signed URLs on Cloud Run)
gcloud iam service-accounts add-iam-policy-binding $SA \
  --member="serviceAccount:$SA" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project=$PROJECT
```

### 4. Authorize Cloud Build to deploy Cloud Run
```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

## Deploying

```bash
export GCP_PROJECT_ID=YOUR_PROJECT_ID
export GCP_REGION=asia-south1
export GCS_VAULT_BUCKET=shotwot-brand-vault-poc
export GCS_OUTPUT_BUCKET=shotwot-generated-outputs-poc
export FIREBASE_PROJECT_ID=YOUR_PROJECT_ID
export SA_EMAIL=shotwot-backend-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com

chmod +x deploy.sh
./deploy.sh
```

The script prints the Cloud Run service URL at the end. Copy it — you need it for the frontend's `VITE_API_URL`.

## After deploying the frontend

Once you have the frontend Cloud Run URL, update the backend's CORS env var:

```bash
gcloud run services update shotwot-backend \
  --region=asia-south1 \
  --update-env-vars="FRONTEND_URL=https://shotwot-frontend-xxx-el.a.run.app,SERVICE_ACCOUNT_EMAIL=shotwot-backend-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com"
```
