#!/usr/bin/env bash
# Run in Google Cloud Shell from the root of the extracted project.
set -euo pipefail
PROJECT_ID="${1:?Uso: bash scripts/deploy.sh TU_PROJECT_ID}"
REGION="${2:-us-central1}"
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com identitytoolkit.googleapis.com compute.googleapis.com
if ! gcloud artifacts repositories describe montecarlo --location "$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create montecarlo --repository-format=docker --location "$REGION"
fi
SA="montecarlo-api@${PROJECT_ID}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA" >/dev/null 2>&1; then
  gcloud iam service-accounts create montecarlo-api --display-name='Monte Carlo API'
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role=roles/datastore.user --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role=roles/firebaseauth.viewer --quiet
BUILD_SA="$(gcloud builds get-default-service-account --project "$PROJECT_ID" | tail -n 1)"
BUILD_SA="${BUILD_SA##*/}"
if [[ ! "$BUILD_SA" == *@*.gserviceaccount.com ]]; then
  echo 'No se pudo resolver la cuenta de Cloud Build. Consulta el manual.' >&2
  exit 1
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${BUILD_SA}" --role=roles/cloudbuild.builds.builder --quiet
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/montecarlo/api:2.0.0"
gcloud builds submit backend --tag "$IMAGE"
gcloud run deploy montecarlo-api --image "$IMAGE" --region "$REGION" --service-account "$SA" --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" --allow-unauthenticated --timeout=90s --concurrency=4 --cpu=1 --memory=512Mi --min-instances=0 --max-instances=3
gcloud run services describe montecarlo-api --region "$REGION" --format='value(status.url)'
