Tests for api-gateway-service

How to run these tests locally:

```bash
cd services/api-gateway-service
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest fastapi[all] httpx
pytest -q
```

Notes:
- The test is a minimal smoke test that checks the `/health` endpoint.
- If importing `main.py` fails due to missing environment variables or optional dependencies, pytest will skip the tests with a helpful message.
