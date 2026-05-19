#!/bin/bash

# ECR Push Script for Rev EvalAI
# This script builds and pushes all Docker images to AWS ECR

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-west-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-407975137156}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
PROJECT_NAME="rev-evalai"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check Docker is running
if ! docker info &> /dev/null; then
    log_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Login to ECR
log_step "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
if [ $? -eq 0 ]; then
    log_info "Successfully logged in to ECR"
else
    log_error "Failed to log in to ECR"
    exit 1
fi

# List of services to build and push
declare -A SERVICES=(
    ["api-gateway"]="./services/api-gateway-service"
    ["user-service"]="./services/user-service"
    ["test-management-service"]="./services/test-management-service"
    ["question-management-service"]="./services/question-management-service"
    ["notification-service"]="./services/notification-service"
    ["ai-quiz-service"]="./services/ai-quiz-service"
    ["ai-interview-service"]="./services/ai-interview-service"
    ["frontend"]="./frontend"
)

# Function to create ECR repository if it doesn't exist
create_ecr_repo() {
    local repo_name=$1

    log_info "Checking if ECR repository ${repo_name} exists..."

    if aws ecr describe-repositories --repository-names ${repo_name} --region $AWS_REGION &> /dev/null; then
        log_info "Repository ${repo_name} already exists"
    else
        log_warn "Repository ${repo_name} does not exist. Creating..."
        aws ecr create-repository \
            --repository-name ${repo_name} \
            --region $AWS_REGION \
            --image_scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 \
            --tags Key=Project,Value="Rev EvalAI" Key=ManagedBy,Value="Script"

        if [ $? -eq 0 ]; then
            log_info "Repository ${repo_name} created successfully"
        else
            log_error "Failed to create repository ${repo_name}"
            return 1
        fi
    fi
}

# Function to build and push image
build_and_push() {
    local service_name=$1
    local service_path=$2
    local repo_name="${PROJECT_NAME}/${service_name}"
    local image_tag="${ECR_REGISTRY}/${repo_name}:latest"
    local commit_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local versioned_tag="${ECR_REGISTRY}/${repo_name}:${commit_sha}"

    echo ""
    log_step "=========================================="
    log_step "Building ${service_name}..."
    log_step "=========================================="

    # Create ECR repository if needed
    create_ecr_repo ${repo_name}

    # Build image
    log_info "Building Docker image from ${service_path}..."

    if [ "$service_name" = "frontend" ]; then
        # For frontend, use production target and pass build args
        # These are required for Next.js NEXT_PUBLIC_* variables
        log_info "Building frontend with build-time environment variables..."

        # Check if ALB URL is set, otherwise use placeholder
        NEXT_PUBLIC_API_GATEWAY_URL="${NEXT_PUBLIC_API_GATEWAY_URL:-http://PLACEHOLDER-UPDATE-AFTER-DEPLOY}"
        NEXT_PUBLIC_WORKOS_REDIRECT_URI="${NEXT_PUBLIC_WORKOS_REDIRECT_URI:-http://PLACEHOLDER-UPDATE-AFTER-DEPLOY/api/auth/callback}"
        NEXT_PUBLIC_INTERVIEW_WS_URL="${NEXT_PUBLIC_INTERVIEW_WS_URL:-ws://PLACEHOLDER-UPDATE-AFTER-DEPLOY:8009}"

        log_info "  NEXT_PUBLIC_API_GATEWAY_URL: ${NEXT_PUBLIC_API_GATEWAY_URL}"

        docker build \
            --platform linux/amd64 \
            --target production \
            --build-arg NEXT_PUBLIC_API_GATEWAY_URL="${NEXT_PUBLIC_API_GATEWAY_URL}" \
            --build-arg NEXT_PUBLIC_WORKOS_REDIRECT_URI="${NEXT_PUBLIC_WORKOS_REDIRECT_URI}" \
            --build-arg NEXT_PUBLIC_INTERVIEW_WS_URL="${NEXT_PUBLIC_INTERVIEW_WS_URL}" \
            -t ${image_tag} -t ${versioned_tag} \
            ${service_path}
    else
        docker build --platform linux/amd64 -t ${image_tag} -t ${versioned_tag} ${service_path}
    fi

    if [ $? -ne 0 ]; then
        log_error "Failed to build ${service_name}"
        return 1
    fi

    # Push both tags
    log_info "Pushing ${image_tag}..."
    docker push ${image_tag}

    if [ $? -ne 0 ]; then
        log_error "Failed to push ${image_tag}"
        return 1
    fi

    log_info "Pushing ${versioned_tag}..."
    docker push ${versioned_tag}

    if [ $? -ne 0 ]; then
        log_error "Failed to push ${versioned_tag}"
        return 1
    fi

    log_info "${GREEN}✓${NC} Successfully pushed ${service_name}"
    return 0
}

# Parse arguments
BUILD_ALL=true
SELECTED_SERVICE=""

if [ $# -gt 0 ]; then
    BUILD_ALL=false
    SELECTED_SERVICE=$1

    if [ -z "${SERVICES[$SELECTED_SERVICE]}" ]; then
        log_error "Unknown service: ${SELECTED_SERVICE}"
        log_info "Available services: ${!SERVICES[@]}"
        exit 1
    fi
fi

# Build and push services
FAILED_SERVICES=()
SUCCESSFUL_SERVICES=()

if [ "$BUILD_ALL" = true ]; then
    log_info "Building and pushing all services..."
    for service in "${!SERVICES[@]}"; do
        if build_and_push $service "${SERVICES[$service]}"; then
            SUCCESSFUL_SERVICES+=($service)
        else
            FAILED_SERVICES+=($service)
        fi
    done
else
    log_info "Building and pushing ${SELECTED_SERVICE} only..."
    if build_and_push $SELECTED_SERVICE "${SERVICES[$SELECTED_SERVICE]}"; then
        SUCCESSFUL_SERVICES+=($SELECTED_SERVICE)
    else
        FAILED_SERVICES+=($SELECTED_SERVICE)
    fi
fi

# Summary
echo ""
log_step "=========================================="
log_step "Build and Push Summary"
log_step "=========================================="
log_info "Successful: ${#SUCCESSFUL_SERVICES[@]}"
log_info "Failed: ${#FAILED_SERVICES[@]}"

if [ ${#SUCCESSFUL_SERVICES[@]} -gt 0 ]; then
    echo ""
    log_info "Successfully pushed images:"
    for service in "${SUCCESSFUL_SERVICES[@]}"; do
        echo "  ${GREEN}✓${NC} ${service}"
    done
fi

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo ""
    log_error "Failed to push images:"
    for service in "${FAILED_SERVICES[@]}"; do
        echo "  ${RED}✗${NC} ${service}"
    done
    exit 1
fi

echo ""
log_step "=========================================="
log_info "${GREEN}✓ All images pushed successfully!${NC}"
log_step "=========================================="
echo ""
log_info "Image URIs (latest tag):"
for service in "${!SERVICES[@]}"; do
    echo "  ${service}: ${ECR_REGISTRY}/${PROJECT_NAME}/${service}:latest"
done
echo ""
log_info "Next steps:"
echo "  1. cd deploy/terraform"
echo "  2. terraform apply"
echo ""
