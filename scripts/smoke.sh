#!/usr/bin/env bash
# Smoke-test each service /health endpoint in dependency order.
# Exits non-zero on the first failure.
set -euo pipefail

USER_URL="${USER_SERVICE_URL:-http://localhost:8002}"
QUESTION_URL="${QUESTION_SERVICE_URL:-http://localhost:8003}"
TEST_MGMT_URL="${TEST_MGMT_SERVICE_URL:-http://localhost:8001}"
GATEWAY_URL="${API_BASE_URL:-http://localhost:8000}"

check() {
    local name="$1"
    local url="$2"
    printf "%-40s" "Checking ${name} ..."
    http_code=$(curl -sf -o /dev/null -w "%{http_code}" "${url}/health" 2>/dev/null || echo "000")
    if [ "${http_code}" = "200" ]; then
        echo "OK"
    else
        echo "FAILED (HTTP ${http_code})"
        exit 1
    fi
}

check "user-service"                 "${USER_URL}"
check "question-management-service"  "${QUESTION_URL}"
check "test-management-service"      "${TEST_MGMT_URL}"
check "api-gateway"                  "${GATEWAY_URL}"

echo "All services healthy."
