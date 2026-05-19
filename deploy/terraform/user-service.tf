# User Service ECS Service and Task Definition

resource "aws_ecs_task_definition" "user_service" {
  family                   = "${var.project_name}-user-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu["user-service"]
  memory                   = var.ecs_task_memory["user-service"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "user-service"
      image     = "${aws_ecr_repository.user_service.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 8002
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "SERVICE_NAME", value = "user-service" },
        { name = "PORT", value = "8002" },
        { name = "SERVICE_HOSTNAME", value = "user-service" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DB_PORT", value = var.existing_db_port },
        { name = "DB_NAME", value = var.user_db_name },
        { name = "ALLOW_ORIGINS", value = "http://${aws_lb.main.dns_name}" },
        { name = "WORKOS_INVITE_URL", value = var.workos_invite_url }
      ]

      secrets = [
        { name = "DB_HOST", valueFrom = local.create_secret_ref.rds.host },
        { name = "DB_USERNAME", valueFrom = local.create_secret_ref.rds.username },
        { name = "DB_PASSWORD", valueFrom = local.create_secret_ref.rds.password },
        { name = "WORKOS_API_KEY", valueFrom = local.create_secret_ref.workos.api_key },
        { name = "WORKOS_CLIENT_ID", valueFrom = local.create_secret_ref.workos.client_id },
        { name = "WORKOS_DEFAULT_ORG", valueFrom = local.create_secret_ref.workos.default_org }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.user_service.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8002/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "user_service" {
  name            = "user-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.user_service.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.user_service.arn
  }


  enable_execute_command = true
}

resource "aws_appautoscaling_target" "user_service" {
  max_capacity       = var.ecs_service_max_count
  min_capacity       = var.ecs_service_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.user_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "user_service_cpu" {
  name               = "${var.project_name}-user-service-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.user_service.resource_id
  scalable_dimension = aws_appautoscaling_target.user_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.user_service.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
