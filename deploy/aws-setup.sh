#!/usr/bin/env bash
# ==============================================================================
# SwarmTwin AWS Infrastructure Provisioning Script
# Creates Amazon S3 bucket and DynamoDB table for disaster triage persistence
# ==============================================================================

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
BUCKET_NAME="${S3_BUCKET_NAME:-swarmtwin-evidence-frames}"
TABLE_NAME="${DYNAMO_TABLE_NAME:-SwarmTwinIncidents}"

echo "=================================================================="
echo " Provisioning SwarmTwin AWS Cloud Infrastructure"
echo " Region:    ${REGION}"
echo " S3:        ${BUCKET_NAME}"
echo " DynamoDB:  ${TABLE_NAME}"
echo "=================================================================="

# 1. Create S3 Bucket
echo "Creating Amazon S3 Bucket: ${BUCKET_NAME}..."
if aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
    echo "✓ S3 Bucket '${BUCKET_NAME}' already exists."
else
    if [[ "${REGION}" == "us-east-1" ]]; then
        aws s3api create-bucket --bucket "${BUCKET_NAME}" --region "${REGION}"
    else
        aws s3api create-bucket --bucket "${BUCKET_NAME}" --region "${REGION}" \
            --create-bucket-configuration LocationConstraint="${REGION}"
    fi
    echo "✓ S3 Bucket '${BUCKET_NAME}' created successfully."
fi

# 2. Create DynamoDB Table
echo "Creating Amazon DynamoDB Table: ${TABLE_NAME}..."
if aws dynamodb describe-table --table-name "${TABLE_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "✓ DynamoDB Table '${TABLE_NAME}' already exists."
else
    aws dynamodb create-table \
        --table-name "${TABLE_NAME}" \
        --attribute-definitions AttributeName=IncidentId,AttributeType=S \
        --key-schema AttributeName=IncidentId,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "${REGION}"
    echo "✓ DynamoDB Table '${TABLE_NAME}' created with on-demand capacity."
fi

echo "=================================================================="
echo "✓ AWS Resources Ready for SwarmTwin Deployment!"
echo "=================================================================="
