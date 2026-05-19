# S3 bucket for interview audio recordings
resource "aws_s3_bucket" "interview_audio" {
  bucket = "${var.project_name}-interview-audio"

  tags = {
    Name        = "${var.project_name}-interview-audio"
    Environment = var.environment
    Purpose     = "Interview audio recordings"
  }
}

# Public access configuration - allow public reads for audio playback
resource "aws_s3_bucket_public_access_block" "interview_audio" {
  bucket = aws_s3_bucket.interview_audio.id

  block_public_acls       = true
  block_public_policy     = false  # Allow bucket policy for public reads
  ignore_public_acls      = true
  restrict_public_buckets = false  # Allow public bucket policy
}

# Bucket policy to allow public read access to audio files
resource "aws_s3_bucket_policy" "interview_audio_public_read" {
  bucket = aws_s3_bucket.interview_audio.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.interview_audio.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.interview_audio]
}

# Enable versioning for interview audio bucket
resource "aws_s3_bucket_versioning" "interview_audio" {
  bucket = aws_s3_bucket.interview_audio.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle policy for interview audio
resource "aws_s3_bucket_lifecycle_configuration" "interview_audio" {
  bucket = aws_s3_bucket.interview_audio.id

  rule {
    id     = "archive-old-recordings"
    status = "Enabled"

    # Apply to all objects (empty prefix matches all)
    filter {}

    # Transition to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Delete after 365 days (adjust based on retention requirements)
    expiration {
      days = 365
    }
  }
}

# CORS configuration for audio playback
resource "aws_s3_bucket_cors_configuration" "interview_audio" {
  bucket = aws_s3_bucket.interview_audio.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "HEAD"]
    allowed_origins = [
      "http://localhost:3000",           # Local development
      "https://${var.domain_name}",      # Production domain
    ]
    expose_headers  = ["ETag", "Content-Length", "Content-Range", "Accept-Ranges"]
    max_age_seconds = 3000
  }
}

# Server-side encryption for interview audio
resource "aws_s3_bucket_server_side_encryption_configuration" "interview_audio" {
  bucket = aws_s3_bucket.interview_audio.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
