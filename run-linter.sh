#!/bin/bash
# run-linter.sh — Run ruff check + format check inside each backend Docker container.
# Usage: bash run-linter.sh

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

CONTAINERS=("rev-eval-api-gateway" "rev-eval-user-service" "rev-eval-test-management" "rev-eval-question-management")
NAMES=("api-gateway-service" "user-service" "test-management-service" "question-management-service")

PASS=0
FAIL=0

echo "======================================================"
echo " ruff lint — backend services"
echo "======================================================"
echo ""

for i in "${!CONTAINERS[@]}"; do
    CONTAINER="${CONTAINERS[$i]}"
    SERVICE="${NAMES[$i]}"
    echo "▶  $SERVICE ($CONTAINER)"

    # Check container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        echo -e "   ${YELLOW}⚠ container not running — skipping${NC}"
        echo ""
        continue
    fi

    # Install ruff if missing
    docker exec "$CONTAINER" pip install --quiet ruff 2>/dev/null || true

    # ruff check
    echo -n "   ruff check  ... "
    if docker exec "$CONTAINER" python -m ruff check /app --output-format=concise 2>&1; then
        echo -e "${GREEN}✓ passed${NC}"
        CHECK_OK=true
    else
        echo -e "${RED}✗ failed${NC}"
        CHECK_OK=false
    fi

    # ruff format --check
    echo -n "   ruff format ... "
    if docker exec "$CONTAINER" python -m ruff format --check /app 2>&1; then
        echo -e "${GREEN}✓ passed${NC}"
        FORMAT_OK=true
    else
        echo -e "${RED}✗ failed${NC}"
        FORMAT_OK=false
    fi

    if $CHECK_OK && $FORMAT_OK; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
    fi

    echo ""
done

echo "======================================================"
echo " Results: ${PASS} passed, ${FAIL} failed"
echo "======================================================"

[ "$FAIL" -eq 0 ]
