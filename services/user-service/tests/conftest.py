import os
import sys
from pathlib import Path

# Settings are created during import, so test env vars must exist first.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "root")
os.environ.setdefault("DB_PASSWORD", "root")
os.environ.setdefault("DB_NAME", "eval_ai_test")

# Ensure pytest can import modules from the service root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import main first to follow the service's normal application import order.
# This avoids triggering the user model/session circular import from schema tests.
import main  # noqa: E402,F401
