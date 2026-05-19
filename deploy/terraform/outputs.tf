# Terraform Outputs for Rev EvalAI

# Load Balancer
output "alb_url" {
  description = "Application Load Balancer URL"
  value       = "http://${aws_lb.main.dns_name}"
}

output "alb_dns_name" {
  description = "ALB DNS name for Route53/domain configuration"
  value       = aws_lb.main.dns_name
}

# ECS Cluster
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

# Cloud Map
output "cloud_map_namespace" {
  description = "Cloud Map private DNS namespace"
  value       = aws_service_discovery_private_dns_namespace.main.name
}

output "cloud_map_namespace_id" {
  description = "Cloud Map namespace ID"
  value       = aws_service_discovery_private_dns_namespace.main.id
}

# ECR Repositories
output "ecr_repositories" {
  description = "ECR repository URLs"
  value = {
    api_gateway          = aws_ecr_repository.api_gateway.repository_url
    user_service         = aws_ecr_repository.user_service.repository_url
    test_management      = aws_ecr_repository.test_management.repository_url
    question_management  = aws_ecr_repository.question_management.repository_url
    notification_service = aws_ecr_repository.notification_service.repository_url
    ai_quiz_service      = aws_ecr_repository.ai_quiz_service.repository_url
    ai_interview_service = aws_ecr_repository.ai_interview_service.repository_url
    frontend             = aws_ecr_repository.frontend.repository_url
  }
}

# VPC
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

# Database
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = var.create_rds ? aws_db_instance.main[0].endpoint : var.existing_db_host
}

# Service URLs (Internal)
output "service_urls" {
  description = "Internal service URLs (Cloud Map DNS)"
  value = {
    api_gateway          = "http://api-gateway.${aws_service_discovery_private_dns_namespace.main.name}:8000"
    user_service         = "http://user-service.${aws_service_discovery_private_dns_namespace.main.name}:8002"
    test_management      = "http://test-management-service.${aws_service_discovery_private_dns_namespace.main.name}:8001"
    question_management  = "http://question-management-service.${aws_service_discovery_private_dns_namespace.main.name}:8003"
    notification_service = "http://notification-service.${aws_service_discovery_private_dns_namespace.main.name}:8004"
    ai_quiz_service      = "http://ai-quiz-service.${aws_service_discovery_private_dns_namespace.main.name}:8005"
    ai_interview_service = "http://ai-interview-service.${aws_service_discovery_private_dns_namespace.main.name}:8009"
  }
}

# CloudWatch Log Groups
output "log_groups" {
  description = "CloudWatch log group names"
  value = {
    api_gateway          = aws_cloudwatch_log_group.api_gateway.name
    user_service         = aws_cloudwatch_log_group.user_service.name
    test_management      = aws_cloudwatch_log_group.test_management.name
    question_management  = aws_cloudwatch_log_group.question_management.name
    notification_service = aws_cloudwatch_log_group.notification_service.name
    ai_quiz_service      = aws_cloudwatch_log_group.ai_quiz_service.name
    ai_interview_service = aws_cloudwatch_log_group.ai_interview_service.name
    frontend             = aws_cloudwatch_log_group.frontend.name
  }
}

# Quick Start Commands
output "useful_commands" {
  description = "Useful AWS CLI commands for managing the deployment"
  value       = <<-EOT
    # View ECS services
    aws ecs list-services --cluster ${aws_ecs_cluster.main.name}

    # View service tasks
    aws ecs list-tasks --cluster ${aws_ecs_cluster.main.name} --service-name api-gateway

    # View logs
    aws logs tail /ecs/api-gateway --follow

    # Update service (force new deployment)
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service api-gateway --force-new-deployment

    # Check Cloud Map services
    aws servicediscovery list-services --region ${var.aws_region}

    # Access the application
    curl http://${aws_lb.main.dns_name}/health
  EOT
}
