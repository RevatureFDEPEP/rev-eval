# Frontend (Next.js) ECS Service and Task Definition

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_task_cpu["frontend"]
  memory                   = var.ecs_task_memory["frontend"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = "${aws_ecr_repository.frontend.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "API_GATEWAY_URL", value = "http://api-gateway.${aws_service_discovery_private_dns_namespace.main.name}:8000" },
        { name = "NEXT_PUBLIC_API_GATEWAY_URL", value = "http://${aws_lb.main.dns_name}" },
        { name = "NEXT_PUBLIC_WORKOS_REDIRECT_URI", value = "http://${aws_lb.main.dns_name}/api/auth/callback" },
        { name = "NEXT_PUBLIC_INTERVIEW_WS_URL", value = "ws://${aws_lb.main.dns_name}/ws/interview" },
        { name = "WORKOS_REDIRECT_URI", value = "http://${aws_lb.main.dns_name}/api/auth/callback" },
        { name = "INTERVIEW_SERVICE_URL", value = "http://ai-interview-service.${aws_service_discovery_private_dns_namespace.main.name}:8009" },
        { name = "ELEVENLABS_VOICE_ID", value = var.elevenlabs_voice_id }
      ]

      secrets = [
        { name = "WORKOS_CLIENT_ID", valueFrom = local.create_secret_ref.workos.client_id },
        { name = "WORKOS_API_KEY", valueFrom = local.create_secret_ref.workos.api_key },
        { name = "WORKOS_DEFAULT_ORG", valueFrom = local.create_secret_ref.workos.default_org },
        { name = "WORKOS_COOKIE_PASSWORD", valueFrom = local.create_secret_ref.workos.cookie_password },
        { name = "ELEVENLABS_API_KEY", valueFrom = local.create_secret_ref.elevenlabs.api_key }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "node -e \"require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})\""]
        interval    = 30
        timeout     = 10
        retries     = 5
        startPeriod = 120
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-frontend"
    Service = "frontend"
  }
}

resource "aws_ecs_service" "frontend" {
  name            = "frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.ecs_service_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }


  enable_execute_command = true

  depends_on = [
    aws_lb_listener.http,
    aws_lb_target_group.frontend
  ]

  tags = {
    Name    = "frontend"
    Service = "frontend"
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "frontend" {
  max_capacity       = var.ecs_service_max_count
  min_capacity       = var.ecs_service_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "frontend_cpu" {
  name               = "${var.project_name}-frontend-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
