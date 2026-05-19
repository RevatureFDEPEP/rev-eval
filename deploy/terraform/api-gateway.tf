# API Gateway ECS Service and Task Definition

# Task Definition
resource "aws_ecs_task_definition" "api_gateway" {
  family                   = "${var.project_name}-api-gateway"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu["api-gateway"]
  memory                   = var.ecs_task_memory["api-gateway"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "api-gateway"
      image     = "${aws_ecr_repository.api_gateway.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "SERVICE_NAME"
          value = "api-gateway"
        },
        {
          name  = "PORT"
          value = "8000"
        },
        {
          name  = "SERVICE_HOSTNAME"
          value = "api-gateway"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "CLOUD_MAP_NAMESPACE"
          value = aws_service_discovery_private_dns_namespace.main.name
        },
        {
          name  = "ALLOW_ORIGINS"
          value = "http://${aws_lb.main.dns_name}"
        }
      ]

      secrets = [
        {
          name      = "WORKOS_API_KEY"
          valueFrom = "${local.create_secret_ref.workos.api_key}"
        },
        {
          name      = "WORKOS_CLIENT_ID"
          valueFrom = "${local.create_secret_ref.workos.client_id}"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api_gateway.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-api-gateway"
    Service = "api-gateway"
  }
}

# ECS Service
resource "aws_ecs_service" "api_gateway" {
  name            = "api-gateway"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api_gateway.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_gateway.arn
    container_name   = "api-gateway"
    container_port   = 8000
  }

  service_registries {
    registry_arn = aws_service_discovery_service.api_gateway.arn
  }


  enable_execute_command = true

  depends_on = [
    aws_lb_listener.http,
    aws_lb_target_group.api_gateway
  ]

  tags = {
    Name    = "api-gateway"
    Service = "api-gateway"
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "api_gateway" {
  max_capacity       = var.ecs_service_max_count
  min_capacity       = var.ecs_service_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api_gateway.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "api_gateway_cpu" {
  name               = "${var.project_name}-api-gateway-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api_gateway.resource_id
  scalable_dimension = aws_appautoscaling_target.api_gateway.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api_gateway.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
