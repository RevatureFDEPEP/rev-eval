"""Test configuration for question-management-service.

Settings require a few env vars at import time (e.g. SERVICE_NAME). Set them
here — conftest is imported before any test module — so importing the app code
under test never fails on missing configuration.
"""
import os

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("S3_ENDPOINT_URL", "http://minio:9000")
os.environ.setdefault("S3_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
os.environ.setdefault("S3_SECRET_KEY", "minioadmin")
os.environ.setdefault("S3_BUCKET_NAME", "question-images")
