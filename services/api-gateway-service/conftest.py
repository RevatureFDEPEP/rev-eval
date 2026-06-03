"""Test bootstrap for the API Gateway.

Imported by pytest before test collection. Sets the env the auth middleware
needs (JWT_SECRET) so importing `main` / the auth module never raises during
a hermetic test run.
"""
import os

os.environ.setdefault("JWT_SECRET", "test-secret-key-0123456789abcdef-32b")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
