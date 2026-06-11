"""Test configuration for question-management-service.

Lives at the service root so pytest (prepend import mode) puts this directory
on sys.path, making `import src.*` resolve. Settings also require a few env
vars at import time (e.g. SERVICE_NAME) — set them here, before any test module
imports the app code, so importing under test never fails on missing config.
"""
import os

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("S3_ENDPOINT_URL", "http://minio:9000")
os.environ.setdefault("S3_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
os.environ.setdefault("S3_SECRET_KEY", "minioadmin")
os.environ.setdefault("S3_BUCKET_NAME", "question-images")
