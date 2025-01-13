#!/bin/bash

# Variables
PROJECT_ID="deductly-447220"
LOCATION="us-central1"
REPOSITORY="deductly"
CLOUD_RUN_NAME="deductly-backend"
IMAGE="deductly-backend"
TAG="latest"

# Set the path to your service account key file
export GOOGLE_APPLICATION_CREDENTIALS="key.json"

# Authenticate with Google Cloud using the service account
gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS

# Set your project ID
gcloud config set project $PROJECT_ID

# Set default region for Cloud Run (optional)
gcloud config set run/region $LOCATION

gcloud auth configure-docker $LOCATION-docker.pkg.dev --quiet



IMAGE_NAME=$LOCATION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE
IMAGE_URI=$IMAGE_NAME:$TAG

# Build Docker image
docker build -t $IMAGE_URI .

# Push the Docker image to Google Artifact Registry
docker push $IMAGE_URI

# Deploy to Cloud Run
gcloud run deploy $CLOUD_RUN_NAME \
  --image=$IMAGE_URI \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=2G \
  --cpu=2
  