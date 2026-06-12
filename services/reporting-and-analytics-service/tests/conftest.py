import os
import sys
from pathlib import Path

# Settings are created at import time; provide deterministic test env.
os.environ.setdefault("SERVICE_NAME", "reporting-and-analytics-service")
os.environ.setdefault("PORT", "8004")
os.environ.setdefault("ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("TEST_MANAGEMENT_URL", "http://test-management-service:8001")

# Ensure pytest can import modules from the service root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
