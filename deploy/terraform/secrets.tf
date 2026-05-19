# AWS Secrets Manager Configuration
# Handles secrets stored as JSON objects in AWS Secrets Manager

# Secrets are stored at: prod/rev-evalai/rds, prod/rev-evalai/mongo, etc.
# Each secret contains JSON with multiple key-value pairs

locals {
  # Secret ARN prefixes
  secret_prefix = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:prod/${var.project_name}"

  # RDS secret path (JSON format)
  # Contains: db-host, db-username, db-password
  rds_secret_arn = "${local.secret_prefix}/rds"

  # MongoDB secret path (JSON format)
  # Contains: mongo-user, mongo-password, mongo-cluster, mongo-db, mongo-appname
  mongo_secret_arn = "${local.secret_prefix}/mongo"

  # WorkOS secret path (JSON format)
  # Contains: workos-api-key, workos-client-id, workos-default-org, workos-cookie-password
  workos_secret_arn = "${local.secret_prefix}/workos"

  # ElevenLabs secret path (JSON format)
  # Contains: elevenlabs-api-key
  elevenlabs_secret_arn = "${local.secret_prefix}/elevenlabs"

  # Helper to create secret reference with JSON key
  # Format for JSON secrets: arn:aws:secretsmanager:region:account:secret:name:json-key::
  # Your secrets use dashes (mongo-user, not mongo_user) - this is correct!
  create_secret_ref = {
    rds = {
      host     = "${local.rds_secret_arn}:db-host::"
      username = "${local.rds_secret_arn}:db-username::"
      password = "${local.rds_secret_arn}:db-password::"
    }
    mongo = {
      user     = "${local.mongo_secret_arn}:mongo-user::"
      password = "${local.mongo_secret_arn}:mongo-password::"
      cluster  = "${local.mongo_secret_arn}:mongo-cluster::"
      db       = "${local.mongo_secret_arn}:mongo-db::"
      appname  = "${local.mongo_secret_arn}:mongo-appname::"
    }
    workos = {
      api_key         = "${local.workos_secret_arn}:workos-api-key::"
      client_id       = "${local.workos_secret_arn}:workos-client-id::"
      default_org     = "${local.workos_secret_arn}:workos-default-org::"
      cookie_password = "${local.workos_secret_arn}:workos-cookie-password::"
    }
    elevenlabs = {
      api_key = "${local.elevenlabs_secret_arn}:elevenlabs-api-key::"
    }
  }
}

# Note: Additional secrets can be created as individual secrets for simpler values
# Example: invite token secret (simple string, not JSON)
resource "aws_secretsmanager_secret" "invite_token" {
  name        = "prod/${var.project_name}/invite-token-secret"
  description = "Secret token for user invitations"

  tags = {
    Name = "invite-token-secret"
  }
}

resource "aws_secretsmanager_secret_version" "invite_token" {
  secret_id     = aws_secretsmanager_secret.invite_token.id
  secret_string = random_password.invite_token.result
}

resource "random_password" "invite_token" {
  length  = 32
  special = true
}
