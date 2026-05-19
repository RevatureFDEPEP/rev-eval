# CloudWatch Log Groups for ECS Services

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/ecs/rev-evalai/api-gateway"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "api-gateway-logs"
    Service = "api-gateway"
  }
}

resource "aws_cloudwatch_log_group" "user_service" {
  name              = "/ecs/rev-evalai/user-service"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "user-service-logs"
    Service = "user-service"
  }
}

resource "aws_cloudwatch_log_group" "test_management" {
  name              = "/ecs/rev-evalai/test-management"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "test-management-logs"
    Service = "test-management"
  }
}

resource "aws_cloudwatch_log_group" "question_management" {
  name              = "/ecs/rev-evalai/question-management"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "question-management-logs"
    Service = "question-management"
  }
}

resource "aws_cloudwatch_log_group" "notification_service" {
  name              = "/ecs/rev-evalai/notification-service"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "notification-service-logs"
    Service = "notification-service"
  }
}

resource "aws_cloudwatch_log_group" "ai_quiz_service" {
  name              = "/ecs/rev-evalai/ai-quiz-service"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "ai-quiz-service-logs"
    Service = "ai-quiz-service"
  }
}

resource "aws_cloudwatch_log_group" "ai_interview_service" {
  name              = "/ecs/rev-evalai/ai-interview-service"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "ai-interview-service-logs"
    Service = "ai-interview-service"
  }
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/rev-evalai/frontend"
  retention_in_days = var.log_retention_days

  tags = {
    Name    = "frontend-logs"
    Service = "frontend"
  }
}

# ============================================================================
# Security Monitoring - VPC Flow Logs Analysis
# ============================================================================

# SNS Topic for Security Alerts
resource "aws_sns_topic" "security_alerts" {
  name = "${var.project_name}-security-alerts"

  tags = {
    Name = "${var.project_name}-security-alerts"
  }
}

# SNS Topic Subscription (replace with your email)
# Uncomment and add your email address to receive alerts
# resource "aws_sns_topic_subscription" "security_alerts_email" {
#   topic_arn = aws_sns_topic.security_alerts.arn
#   protocol  = "email"
#   endpoint  = "your-security-team@example.com"
# }

# Metric Filter: Detect Port 23 (Telnet) Connection Attempts
resource "aws_cloudwatch_log_metric_filter" "port_23_scanning" {
  name           = "${var.project_name}-port-23-scanning"
  log_group_name = aws_cloudwatch_log_group.vpc_flow_logs.name

  # Pattern matches VPC Flow Logs with destination port 23
  # Format: version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
  pattern = "[version, account, eni, source, destination, srcport, dstport=23, protocol, packets, bytes, start, end, action, logstatus]"

  metric_transformation {
    name      = "Port23Connections"
    namespace = "${var.project_name}/Security"
    value     = "1"
    unit      = "Count"
  }
}

# Metric Filter: Detect Port 22 (SSH) Scanning Attempts
resource "aws_cloudwatch_log_metric_filter" "port_22_scanning" {
  name           = "${var.project_name}-port-22-scanning"
  log_group_name = aws_cloudwatch_log_group.vpc_flow_logs.name

  pattern = "[version, account, eni, source, destination, srcport, dstport=22, protocol, packets, bytes, start, end, action=REJECT, logstatus]"

  metric_transformation {
    name      = "Port22RejectedConnections"
    namespace = "${var.project_name}/Security"
    value     = "1"
    unit      = "Count"
  }
}

# Metric Filter: Detect High Volume of Rejected Connections (potential scanning)
resource "aws_cloudwatch_log_metric_filter" "rejected_connections" {
  name           = "${var.project_name}-rejected-connections"
  log_group_name = aws_cloudwatch_log_group.vpc_flow_logs.name

  pattern = "[version, account, eni, source, destination, srcport, dstport, protocol, packets, bytes, start, end, action=REJECT, logstatus]"

  metric_transformation {
    name      = "RejectedConnections"
    namespace = "${var.project_name}/Security"
    value     = "1"
    unit      = "Count"
  }
}

# Alarm: Port 23 Scanning Detected
resource "aws_cloudwatch_metric_alarm" "port_23_scanning_alarm" {
  alarm_name          = "${var.project_name}-port-23-scanning-detected"
  alarm_description   = "Alert when telnet port 23 connection attempts are detected"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Port23Connections"
  namespace           = "${var.project_name}/Security"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5 # Alert if more than 5 port 23 connections in 5 minutes
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.security_alerts.arn]

  tags = {
    Name     = "${var.project_name}-port-23-alarm"
    Severity = "High"
  }
}

# Alarm: High Volume of Rejected Connections (Potential Scanning)
resource "aws_cloudwatch_metric_alarm" "high_rejected_connections" {
  alarm_name          = "${var.project_name}-high-rejected-connections"
  alarm_description   = "Alert when high volume of rejected connections detected (potential port scanning)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RejectedConnections"
  namespace           = "${var.project_name}/Security"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 100 # Alert if more than 100 rejected connections in 5 minutes
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.security_alerts.arn]

  tags = {
    Name     = "${var.project_name}-rejected-connections-alarm"
    Severity = "Medium"
  }
}

# Metric Filter: Detect RCE Attempts in Frontend Logs
resource "aws_cloudwatch_log_metric_filter" "rce_attempts" {
  name           = "${var.project_name}-rce-attempts"
  log_group_name = aws_cloudwatch_log_group.frontend.name

  # Detect common RCE patterns: curl, wget, bash downloads
  pattern = "?curl ?wget ?bash ?exec ?spawn ?child_process"

  metric_transformation {
    name      = "RCEAttempts"
    namespace = "${var.project_name}/Security"
    value     = "1"
    unit      = "Count"
  }
}

# Alarm: RCE Attempt Detected
resource "aws_cloudwatch_metric_alarm" "rce_attempts_alarm" {
  alarm_name          = "${var.project_name}-rce-attempts-detected"
  alarm_description   = "Alert when potential RCE attempts are detected in frontend logs"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RCEAttempts"
  namespace           = "${var.project_name}/Security"
  period              = 60 # 1 minute
  statistic           = "Sum"
  threshold           = 1 # Alert on any RCE attempt
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.security_alerts.arn]

  tags = {
    Name     = "${var.project_name}-rce-alarm"
    Severity = "Critical"
  }
}
