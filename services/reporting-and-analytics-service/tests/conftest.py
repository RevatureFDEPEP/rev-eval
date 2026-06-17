import os

# Force required settings before `src` is imported so Settings() validates.
# No JWT_SECRET: this service reads the X-User-Role header injected by the
# gateway and never decodes JWTs (platform auth contract).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "reporting-and-analytics-service")
os.environ.setdefault("PORT", "8004")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
