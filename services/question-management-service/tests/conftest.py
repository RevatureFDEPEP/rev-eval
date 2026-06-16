# IMPORTANT: set env vars BEFORE any app imports so pydantic-settings picks
# them up. `SERVICE_NAME` has no default in settings.py, and the S3 settings
# are read at import time by src/utils/s3_client.py.
import os

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/evalai_test")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "testaccess")
os.environ.setdefault("S3_SECRET_KEY", "testsecret")
os.environ.setdefault("S3_BUCKET_NAME", "question-images-test")
os.environ.setdefault("S3_REGION", "us-east-1")
os.environ.setdefault("S3_PRESIGN_EXPIRY_SECONDS", "3600")
