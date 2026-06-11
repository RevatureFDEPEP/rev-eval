#!/usr/bin/env bash
#
# W3-F6 smoke test: confirm every HTTP service answers /health before any
# browser test runs. Checks run in dependency order so the first failure
# points at the root cause, not a downstream symptom.
#
# A fresh script rather than a test-services.sh extension — that file predates
# the current compose topology (Consul/WorkOS/Lambda) and checks services that
# do not exist. docker-compose.yml is the source of truth.
#
# Usage: ./scripts/smoke.sh   (stack already up: docker compose up -d --wait)
# Exits non-zero naming the first unhealthy service.

set -u

# service-name  url  attempts
# Frontend gets a long budget: the compose dev server compiles on demand.
CHECKS=(
  "user-service|http://localhost:8002/health|30"
  "question-management-service|http://localhost:8003/health|30"
  "test-management-service|http://localhost:8001/health|30"
  "reporting-and-analytics-service|http://localhost:8004/health|30"
  "api-gateway-service|http://localhost:8000/health|30"
  "frontend|http://localhost:3000/|90"
)

for check in "${CHECKS[@]}"; do
  IFS='|' read -r name url attempts <<< "$check"
  ok=0
  for ((i = 1; i <= attempts; i++)); do
    status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url" || true)
    if [ "$status" = "200" ]; then
      echo "✅ ${name} healthy (${url})"
      ok=1
      break
    fi
    sleep 2
  done
  if [ "$ok" -ne 1 ]; then
    echo "❌ ${name} unhealthy: ${url} last status '${status}' after ${attempts} attempts" >&2
    exit 1
  fi
done

echo "✅ smoke passed — all services healthy"
