#!/bin/bash

# Verification Script for AWS Secrets Manager Setup
# This script checks that all required secrets exist and have the correct format

set -e

AWS_REGION="us-west-1"
PROJECT_NAME="rev-evalai"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AWS Secrets Manager Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ AWS CLI installed${NC}"

# Check jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq is not installed (required for JSON parsing)${NC}"
    exit 1
fi
echo -e "${GREEN}✅ jq installed${NC}"

echo ""

# Function to check secret
check_secret() {
    local secret_id=$1
    local required_keys=$2

    echo -e "${YELLOW}Checking secret: ${secret_id}${NC}"

    # Check if secret exists
    if ! aws secretsmanager get-secret-value \
        --secret-id "${secret_id}" \
        --region ${AWS_REGION} \
        --query SecretString \
        --output text &> /dev/null; then
        echo -e "${RED}  ❌ Secret not found${NC}"
        return 1
    fi

    # Get secret value
    SECRET_VALUE=$(aws secretsmanager get-secret-value \
        --secret-id "${secret_id}" \
        --region ${AWS_REGION} \
        --query SecretString \
        --output text)

    # Check if valid JSON
    if ! echo "${SECRET_VALUE}" | jq empty &> /dev/null; then
        echo -e "${RED}  ❌ Secret value is not valid JSON${NC}"
        return 1
    fi

    echo -e "${GREEN}  ✅ Secret exists and is valid JSON${NC}"

    # Check required keys
    IFS=',' read -ra KEYS <<< "$required_keys"
    local missing_keys=()

    for key in "${KEYS[@]}"; do
        if ! echo "${SECRET_VALUE}" | jq -e ".\"${key}\"" &> /dev/null; then
            missing_keys+=("${key}")
        fi
    done

    if [ ${#missing_keys[@]} -gt 0 ]; then
        echo -e "${RED}  ❌ Missing keys: ${missing_keys[*]}${NC}"
        return 1
    fi

    echo -e "${GREEN}  ✅ All required keys present${NC}"
    echo ""
    return 0
}

# Check all secrets
total_checks=0
passed_checks=0

# RDS
((total_checks++))
if check_secret "prod/${PROJECT_NAME}/rds" "db-host,db-username,db-password,db-name,user-db-name"; then
    ((passed_checks++))
fi

# MongoDB
((total_checks++))
if check_secret "prod/${PROJECT_NAME}/mongo" "mongo-user,mongo-password,mongo-cluster,mongo-db,mongo-appname"; then
    ((passed_checks++))
fi

# WorkOS
((total_checks++))
if check_secret "prod/${PROJECT_NAME}/workos" "workos-api-key,workos-client-id,workos-default-org,workos-cookie-password,workos-invite-url"; then
    ((passed_checks++))
fi

# ElevenLabs
((total_checks++))
if check_secret "prod/${PROJECT_NAME}/elevenlabs" "elevenlabs-api-key"; then
    ((passed_checks++))
fi

# SES
((total_checks++))
if check_secret "prod/${PROJECT_NAME}/ses" "ses-sender-email"; then
    ((passed_checks++))
fi

# Frontend
((total_checks++))
if check_secret "prod/${PROJECT_NAME}/frontend" "next-public-api-gateway-url,next-public-workos-redirect-uri,next-public-interview-ws-url"; then
    ((passed_checks++))
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total checks: ${total_checks}"
echo -e "Passed: ${GREEN}${passed_checks}${NC}"
echo -e "Failed: ${RED}$((total_checks - passed_checks))${NC}"
echo ""

if [ ${passed_checks} -eq ${total_checks} ]; then
    echo -e "${GREEN}✅ All secrets are configured correctly!${NC}"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Verify AWS credentials in GitHub Secrets"
    echo "2. Push to main branch to trigger deployment"
    exit 0
else
    echo -e "${RED}❌ Some secrets are missing or misconfigured${NC}"
    echo ""
    echo -e "${YELLOW}Please fix the issues above before deploying${NC}"
    echo "See deploy/GITHUB-SECRETS-SETUP.md for instructions"
    exit 1
fi
