# Question Management, Notification, and AI Interview Services

# ========== Question Management Service ==========

resource "aws_ecs_task_definition" "question_management" {
  family                   = "${var.project_name}-question-management"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu["question-management"]
  memory                   = var.ecs_task_memory["question-management"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name         = "question-management"
      image        = "${aws_ecr_repository.question_management.repository_url}:${var.image_tag}"
      essential    = true
      portMappings = [{ containerPort = 8003, protocol = "tcp" }]
      environment = [
        { name = "SERVICE_NAME", value = "question-management-service" },
        { name = "PORT", value = "8003" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "ALLOW_ORIGINS", value = "http://${aws_lb.main.dns_name}" }
      ]
      secrets = [
        { name = "MONGO_USER", valueFrom = local.create_secret_ref.mongo.user },
        { name = "MONGODB_PASSWORD", valueFrom = local.create_secret_ref.mongo.password },
        { name = "MONGO_CLUSTER", valueFrom = local.create_secret_ref.mongo.cluster },
        { name = "MONGO_DB", valueFrom = local.create_secret_ref.mongo.db },
        { name = "MONGO_APPNAME", valueFrom = local.create_secret_ref.mongo.appname }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.question_management.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8003/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "question_management" {
  name            = "question-management-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.question_management.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  service_registries {
    registry_arn = aws_service_discovery_service.question_management.arn
  }
  enable_execute_command = true
}

# ========== Notification Service ==========

resource "aws_ecs_task_definition" "notification_service" {
  family                   = "${var.project_name}-notification-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu["notification-service"]
  memory                   = var.ecs_task_memory["notification-service"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name         = "notification-service"
      image        = "${aws_ecr_repository.notification_service.repository_url}:${var.image_tag}"
      essential    = true
      portMappings = [{ containerPort = 8004, protocol = "tcp" }]
      environment = [
        { name = "SERVICE_NAME", value = "notification-service" },
        { name = "PORT", value = "8004" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DB_PORT", value = var.existing_db_port },
        { name = "DB_NAME", value = var.db_name },
        { name = "SES_SENDER_EMAIL", value = var.ses_sender_email },
        { name = "SES_SENDER_NAME", value = var.ses_sender_name },
        { name = "FRONTEND_URL", value = "http://${aws_lb.main.dns_name}" },
        { name = "SQS_QUEUE_URL", value = var.notification_sqs_queue_url },
        { name = "SQS_ENABLED", value = "True" },
        { name = "ALLOW_ORIGINS", value = "http://${aws_lb.main.dns_name}" }
      ]
      secrets = [
        { name = "DB_HOST", valueFrom = local.create_secret_ref.rds.host },
        { name = "DB_USERNAME", valueFrom = local.create_secret_ref.rds.username },
        { name = "DB_PASSWORD", valueFrom = local.create_secret_ref.rds.password },
        { name = "INVITE_TOKEN_SECRET", valueFrom = aws_secretsmanager_secret.invite_token.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.notification_service.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8004/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "notification_service" {
  name            = "notification-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.notification_service.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  service_registries {
    registry_arn = aws_service_discovery_service.notification_service.arn
  }
  enable_execute_command = true
}

# ========== AI Interview Service ==========

resource "aws_ecs_task_definition" "ai_interview_service" {
  family                   = "${var.project_name}-ai-interview-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu["ai-interview-service"]
  memory                   = var.ecs_task_memory["ai-interview-service"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name         = "ai-interview-service"
      image        = "${aws_ecr_repository.ai_interview_service.repository_url}:${var.image_tag}"
      essential    = true
      portMappings = [{ containerPort = 8009, protocol = "tcp" }]
      environment = [
        { name = "SERVICE_NAME", value = "ai-interview-service" },
        { name = "PORT", value = "8009" },
        { name = "SERVICE_HOSTNAME", value = "ai-interview-service" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "TEST_SERVICE_URL", value = "http://test-management-service.${aws_service_discovery_private_dns_namespace.main.name}:8001" },
        { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
        { name = "BEDROCK_MAX_TOKENS", value = tostring(var.bedrock_max_tokens) },
        { name = "BEDROCK_TEMPERATURE", value = tostring(var.bedrock_temperature) },
        { name = "LANGSMITH_TRACING", value = "false" },
        { name = "SQS_QUEUE_URL", value = var.interview_sqs_queue_url },
        { name = "SQS_ENABLED", value = "True" },
        { name = "S3_INTERVIEW_AUDIO_BUCKET", value = aws_s3_bucket.interview_audio.id },
        { name = "ALLOW_ORIGINS", value = "[\"http://${aws_lb.main.dns_name}\"]" }
      ]
      secrets = [
        { name = "MONGO_USER", valueFrom = local.create_secret_ref.mongo.user },
        { name = "MONGODB_PASSWORD", valueFrom = local.create_secret_ref.mongo.password },
        { name = "MONGO_CLUSTER", valueFrom = local.create_secret_ref.mongo.cluster },
        { name = "MONGO_DB", valueFrom = local.create_secret_ref.mongo.db },
        { name = "MONGO_APPNAME", valueFrom = local.create_secret_ref.mongo.appname }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ai_interview_service.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8009/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "ai_interview_service" {
  name            = "ai-interview-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ai_interview_service.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.ai_interview.arn
    container_name   = "ai-interview-service"
    container_port   = 8009
  }
  service_registries {
    registry_arn = aws_service_discovery_service.ai_interview_service.arn
  }
  enable_execute_command = true
}
