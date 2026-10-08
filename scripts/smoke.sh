#!/usr/bin/env bash
# Smoke-test the running stack. Exits non-zero on the first failure.
#
#   ./scripts/smoke.sh            through Nginx (base stack): HTTP redirect, HTTPS front door,
#                                 gateway health, and an unauthenticated API call rejected with 401
#   ./scripts/smoke.sh --direct   each service /health on its own port; needs the dev override
#                                 (docker compose -f docker-compose.yml -f docker-compose.dev.yml up)
set -euo pipefail

BASE_URL="${BASE_URL:-https://localhost}"

USER_URL="${USER_SERVICE_URL:-http://localhost:8002}"
QUESTION_URL="${QUESTION_SERVICE_URL:-http://localhost:8003}"
TEST_MGMT_URL="${TEST_MGMT_SERVICE_URL:-http://localhost:8001}"
REPORTING_URL="${REPORTING_SERVICE_URL:-http://localhost:8004}"
GATEWAY_URL="${API_BASE_URL:-http://localhost:8000}"

# expect <name> <url> <expected HTTP code>
expect() {
    local name="$1" url="$2" want="$3" code
    printf "%-44s" "Checking ${name} ..."
    # -k: the local Nginx certificate is self-signed.
    code=$(curl -sk -o /dev/null -w "%{http_code}" "${url}" 2>/dev/null || true)
    if [ "${code}" = "${want}" ]; then
        echo "OK (${code})"
    else
        echo "FAILED (HTTP ${code:-000}, expected ${want})"
        exit 1
    fi
}

if [ "${1:-}" = "--direct" ]; then
    expect "user-service /health"            "${USER_URL}/health"      200
    expect "question-management /health"     "${QUESTION_URL}/health"  200
    expect "test-management /health"         "${TEST_MGMT_URL}/health" 200
    expect "reporting-and-analytics /health" "${REPORTING_URL}/health" 200
    expect "api-gateway /health"             "${GATEWAY_URL}/health"   200
else
    expect "HTTP redirects to HTTPS"         "http://${BASE_URL#https://}/" 301
    expect "frontend via Nginx"              "${BASE_URL}/"                 200
    expect "gateway /health via Nginx"       "${BASE_URL}/health"           200
    expect "API without a token is rejected" "${BASE_URL}/v1/api/tests/"    401
fi

echo "All checks passed."
