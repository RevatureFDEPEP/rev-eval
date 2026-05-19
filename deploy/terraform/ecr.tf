# ECR (Elastic Container Registry) Configuration for Rev EvalAI
# Private repositories for all Docker images

# API Gateway
resource "aws_ecr_repository" "api_gateway" {
  name                 = "${var.project_name}/api-gateway"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "api-gateway"
    Service = "api-gateway"
  }
}

# User Service
resource "aws_ecr_repository" "user_service" {
  name                 = "${var.project_name}/user-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "user-service"
    Service = "user-service"
  }
}

# Test Management Service
resource "aws_ecr_repository" "test_management" {
  name                 = "${var.project_name}/test-management-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "test-management-service"
    Service = "test-management"
  }
}

# Question Management Service
resource "aws_ecr_repository" "question_management" {
  name                 = "${var.project_name}/question-management-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "question-management-service"
    Service = "question-management"
  }
}

# Notification Service
resource "aws_ecr_repository" "notification_service" {
  name                 = "${var.project_name}/notification-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "notification-service"
    Service = "notification-service"
  }
}

# AI Quiz Service
resource "aws_ecr_repository" "ai_quiz_service" {
  name                 = "${var.project_name}/ai-quiz-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "ai-quiz-service"
    Service = "ai-quiz-service"
  }
}

# AI Interview Service
resource "aws_ecr_repository" "ai_interview_service" {
  name                 = "${var.project_name}/ai-interview-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "ai-interview-service"
    Service = "ai-interview-service"
  }
}

# Frontend
resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}/frontend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "frontend"
    Service = "frontend"
  }
}

# Lifecycle policy to keep only recent images (cost optimization)
resource "aws_ecr_lifecycle_policy" "main" {
  for_each = {
    api_gateway          = aws_ecr_repository.api_gateway.name
    user_service         = aws_ecr_repository.user_service.name
    test_management      = aws_ecr_repository.test_management.name
    question_management  = aws_ecr_repository.question_management.name
    notification_service = aws_ecr_repository.notification_service.name
    ai_quiz_service      = aws_ecr_repository.ai_quiz_service.name
    ai_interview_service = aws_ecr_repository.ai_interview_service.name
    frontend             = aws_ecr_repository.frontend.name
  }

  repository = each.value

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
