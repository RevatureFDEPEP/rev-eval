# Terraform Variables for Rev EvalAI ECS Deployment

# AWS Configuration
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
  default     = "407975137156"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "rev-evalai"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["us-west-1a", "us-west-1c"]
}

# ECS Configuration
variable "ecs_task_cpu" {
  description = "CPU units for ECS tasks (256 = 0.25 vCPU)"
  type        = map(string)
  default = {
    api-gateway          = "256"
    user-service         = "256"
    test-management      = "512"
    question-management  = "256"
    notification-service = "256"
    ai-quiz-service      = "512"
    ai-interview-service = "512"
    frontend             = "512"
  }
}

variable "ecs_task_memory" {
  description = "Memory for ECS tasks in MB"
  type        = map(string)
  default = {
    api-gateway          = "512"
    user-service         = "512"
    test-management      = "1024"
    question-management  = "512"
    notification-service = "512"
    ai-quiz-service      = "1024"
    ai-interview-service = "1024"
    frontend             = "1024"
  }
}

variable "ecs_service_desired_count" {
  description = "Desired number of tasks per service"
  type        = number
  default     = 1
}

variable "ecs_service_min_count" {
  description = "Minimum number of tasks for auto-scaling"
  type        = number
  default     = 1
}

variable "ecs_service_max_count" {
  description = "Maximum number of tasks for auto-scaling"
  type        = number
  default     = 3
}

# Database Configuration
variable "create_rds" {
  description = "Whether to create RDS PostgreSQL instance"
  type        = bool
  default     = false # Set to true if you don't have RDS yet
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Database name (used by most services)"
  type        = string
  default     = "evalai"
}

variable "user_db_name" {
  description = "Database name for user service (separate database on same RDS instance)"
  type        = string
  default     = "evalai_users"
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Existing RDS (if create_rds = false)
variable "existing_db_host" {
  description = "Existing RDS endpoint (if not creating new RDS)"
  type        = string
  default     = ""
}

variable "existing_db_port" {
  description = "Existing RDS port"
  type        = string
  default     = "5432"
}

# MongoDB Atlas (External)
variable "mongo_user" {
  description = "MongoDB Atlas username"
  type        = string
  sensitive   = true
}

variable "mongo_password" {
  description = "MongoDB Atlas password"
  type        = string
  sensitive   = true
}

variable "mongo_cluster" {
  description = "MongoDB Atlas cluster URL"
  type        = string
}

variable "mongo_db" {
  description = "MongoDB database name"
  type        = string
  default     = "evalai"
}

variable "mongo_appname" {
  description = "MongoDB application name"
  type        = string
  default     = "EvalAI"
}

# WorkOS Configuration
variable "workos_api_key" {
  description = "WorkOS API key"
  type        = string
  sensitive   = true
}

variable "workos_client_id" {
  description = "WorkOS client ID"
  type        = string
  sensitive   = true
}

variable "workos_default_org" {
  description = "WorkOS default organization ID"
  type        = string
  sensitive   = true
}

variable "workos_cookie_password" {
  description = "WorkOS cookie password (32+ characters)"
  type        = string
  sensitive   = true
}

variable "workos_invite_url" {
  description = "WorkOS invite URL"
  type        = string
  default     = "https://therapeutic-arch-47-staging.authkit.app/invite"
}

# ElevenLabs Configuration
variable "elevenlabs_api_key" {
  description = "ElevenLabs API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "elevenlabs_voice_id" {
  description = "ElevenLabs voice ID"
  type        = string
  default     = "s3TPKV1kjDlVtZbl4Ksh"
}

# AWS Services Configuration
variable "ai_quiz_sqs_queue_url" {
  description = "SQS queue URL for quiz evaluation"
  type        = string
}

variable "test_service_sqs_queue_url" {
  description = "SQS queue URL for test management notifications"
  type        = string
}

variable "notification_sqs_queue_url" {
  description = "SQS queue URL for notification service"
  type        = string
}

variable "interview_sqs_queue_url" {
  description = "SQS queue URL for interview evaluation"
  type        = string
}

variable "ses_sender_email" {
  description = "AWS SES sender email address"
  type        = string
}

variable "ses_sender_name" {
  description = "AWS SES sender name"
  type        = string
  default     = "Rev EvalAI"
}

# AWS Bedrock Configuration
variable "bedrock_model_id" {
  description = "AWS Bedrock model ID (using cross-region inference endpoint)"
  type        = string
  default     = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
}

variable "bedrock_max_tokens" {
  description = "Bedrock max tokens"
  type        = number
  default     = 2048
}

variable "bedrock_temperature" {
  description = "Bedrock temperature"
  type        = number
  default     = 0.7
}

# Image Tags
variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

# Domain Configuration (Optional)
variable "domain_name" {
  description = "Custom domain name for the application"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = ""
}

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# Tags
variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "Rev EvalAI"
    ManagedBy   = "Terraform"
    Environment = "production"
  }
}
