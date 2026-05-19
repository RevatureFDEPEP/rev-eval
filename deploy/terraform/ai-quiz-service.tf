# AI Quiz Service ECS Service and Task Definition

resource "aws_ecs_task_definition" "ai_quiz_service" {
  family                   = "${var.project_name}-ai-quiz-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu["ai-quiz-service"]
  memory                   = var.ecs_task_memory["ai-quiz-service"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "ai-quiz-service"
      image     = "${aws_ecr_repository.ai_quiz_service.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 8005
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "SERVICE_NAME", value = "ai-quiz-service" },
        { name = "PORT", value = "8005" },
        { name = "SERVICE_HOSTNAME", value = "ai-quiz-service" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "ALLOW_ORIGINS", value = "http://${aws_lb.main.dns_name}" },
        { name = "TEST_SERVICE_URL", value = "http://test-management-service.${aws_service_discovery_private_dns_namespace.main.name}:8001" },
        { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
        { name = "BEDROCK_MAX_TOKENS", value = tostring(var.bedrock_max_tokens) },
        { name = "BEDROCK_TEMPERATURE", value = tostring(var.bedrock_temperature) },
        { name = "SQS_QUEUE_URL", value = var.ai_quiz_sqs_queue_url },
        { name = "SQS_ENABLED", value = "True" },
        { name = "LANGSMITH_TRACING", value = "false" }
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
          "awslogs-group"         = aws_cloudwatch_log_group.ai_quiz_service.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8005/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "ai_quiz_service" {
  name            = "ai-quiz-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ai_quiz_service.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.ai_quiz_service.arn
  }


  enable_execute_command = true
}

resource "aws_appautoscaling_target" "ai_quiz_service" {
  max_capacity       = var.ecs_service_max_count
  min_capacity       = var.ecs_service_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.ai_quiz_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ai_quiz_service_cpu" {
  name               = "${var.project_name}-ai-quiz-service-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ai_quiz_service.resource_id
  scalable_dimension = aws_appautoscaling_target.ai_quiz_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ai_quiz_service.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
