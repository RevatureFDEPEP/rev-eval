# AWS Cloud Map Service Discovery Configuration
# Replaces Consul for service discovery

# Private DNS Namespace
resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "evalai.local"
  description = "Private DNS namespace for Rev EvalAI services"
  vpc         = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-service-discovery"
  }
}

# Service Discovery Services (one per microservice)
# These are automatically registered by ECS tasks

resource "aws_service_discovery_service" "api_gateway" {
  name = "api-gateway"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name = "api-gateway"
  }
}

resource "aws_service_discovery_service" "user_service" {
  name = "user-service"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name = "user-service"
  }
}

resource "aws_service_discovery_service" "test_management" {
  name = "test-management-service"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name = "test-management-service"
  }
}

resource "aws_service_discovery_service" "question_management" {
  name = "question-management-service"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name = "question-management-service"
  }
}

resource "aws_service_discovery_service" "notification_service" {
  name = "notification-service"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name = "notification-service"
  }
}

resource "aws_service_discovery_service" "ai_quiz_service" {
  name = "ai-quiz-service"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name = "ai-quiz-service"
  }
}

resource "aws_service_discovery_service" "ai_interview_service" {
  name = "ai-interview-service"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name = "ai-interview-service"
  }
}
