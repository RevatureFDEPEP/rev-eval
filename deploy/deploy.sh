#!/bin/bash

# Complete deployment script for Rev EvalAI
# This script handles the full deployment workflow

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker is not running"
        exit 1
    fi

    log_info "All prerequisites met"
}

# Build and push images
build_and_push_images() {
    log_step "Building and pushing Docker images to ECR..."
    ./deploy/ecr-push.sh

    if [ $? -ne 0 ]; then
        log_error "Failed to push images to ECR"
        exit 1
    fi

    log_info "Images pushed successfully"
}

# Deploy infrastructure
deploy_infrastructure() {
    log_step "Deploying infrastructure with Terraform..."

    cd deploy/terraform

    # Initialize Terraform if needed
    if [ ! -d ".terraform" ]; then
        log_info "Initializing Terraform..."
        terraform init
    fi

    # Plan
    log_info "Creating Terraform plan..."
    terraform plan -out=tfplan

    # Apply
    log_info "Applying Terraform changes..."
    terraform apply tfplan

    if [ $? -ne 0 ]; then
        log_error "Terraform apply failed"
        cd ../..
        exit 1
    fi

    log_info "Infrastructure deployed successfully"

    # Show outputs
    echo ""
    log_step "Deployment Complete!"
    echo ""
    terraform output

    cd ../..
}

# Main execution
main() {
    echo ""
    log_step "=========================================="
    log_step "Rev EvalAI Deployment"
    log_step "=========================================="
    echo ""

    check_prerequisites
    build_and_push_images
    deploy_infrastructure

    echo ""
    log_step "=========================================="
    log_info "${GREEN}✓ Deployment completed successfully!${NC}"
    log_step "=========================================="
    echo ""
}

# Run main function
main
