# Test Management Service ECS Service and Task Definition

resource "aws_ecs_task_definition" "test_management" {
  family                   = "${var.project_name}-test-management"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu["test-management"]
  memory                   = var.ecs_task_memory["test-management"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "test-management"
      image     = "${aws_ecr_repository.test_management.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 8001
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "SERVICE_NAME", value = "test-management-service" },
        { name = "PORT", value = "8001" },
        { name = "SERVICE_HOSTNAME", value = "test-management-service" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DB_PORT", value = var.existing_db_port },
        { name = "DB_NAME", value = var.db_name },
        { name = "ALLOW_ORIGINS", value = "http://${aws_lb.main.dns_name}" },
        { name = "USER_SERVICE_URL", value = "http://user-service.${aws_service_discovery_private_dns_namespace.main.name}:8002" },
        { name = "NOTIFICATION_SERVICE_URL", value = "http://notification-service.${aws_service_discovery_private_dns_namespace.main.name}:8004" },
        { name = "INTERVIEW_SERVICE_URL", value = "http://ai-interview-service.${aws_service_discovery_private_dns_namespace.main.name}:8009" },
        { name = "SQS_QUEUE_URL", value = var.test_service_sqs_queue_url },
        { name = "SQS_ENABLED", value = "True" }
      ]

      secrets = [
        { name = "DB_HOST", valueFrom = local.create_secret_ref.rds.host },
        { name = "DB_USERNAME", valueFrom = local.create_secret_ref.rds.username },
        { name = "DB_PASSWORD", valueFrom = local.create_secret_ref.rds.password }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.test_management.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "test_management" {
  name            = "test-management-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.test_management.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.test_management.arn
  }


  enable_execute_command = true
}

resource "aws_appautoscaling_target" "test_management" {
  max_capacity       = var.ecs_service_max_count
  min_capacity       = var.ecs_service_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.test_management.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "test_management_cpu" {
  name               = "${var.project_name}-test-management-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.test_management.resource_id
  scalable_dimension = aws_appautoscaling_target.test_management.scalable_dimension
  service_namespace  = aws_appautoscaling_target.test_management.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
