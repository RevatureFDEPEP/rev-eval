#!/bin/bash

# Service Health Check Script
# Tests all services to ensure they're running correctly

echo "🧪 Rev Eval AI - Service Health Check"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test a service
test_service() {
    local name=$1
    local url=$2
    local expected=$3

    echo -n "Testing $name... "

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

    if [ "$response" == "$expected" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $response, expected $expected)"
        return 1
    fi
}

# Test Consul
echo "1. Consul Service Discovery"
test_service "Consul UI" "http://localhost:8500/ui" "200"
echo ""

# Test API Gateway
echo "2. API Gateway"
test_service "Health Check" "http://localhost:8000/health" "200"
test_service "Routes Endpoint" "http://localhost:8000/routes" "200"
echo ""

# Test Test Management Service
echo "3. Test Management Service"
test_service "Health Check" "http://localhost:8001/health" "200"
test_service "API Docs" "http://localhost:8001/docs" "200"
echo ""

# Test Frontend
echo "4. Frontend"
test_service "Landing Page" "http://localhost:3000" "200"
echo ""

# Test Quiz Evaluation Lambda
echo "5. Quiz Evaluation Lambda"
test_service "Health Check" "http://localhost:9000/health" "200"
echo ""

# Test Database Connection # naming convention mismatch -> eval_ai_test_management
echo "6. Database"
if command -v psql &> /dev/null; then
    if psql -U postgres -d eval_ai_test_management -c "SELECT 1" &> /dev/null; then 
        echo -e "Database Connection... ${GREEN}✓ OK${NC}"

        # Check if tables exist
        table_count=$(psql -U postgres -d eval_ai_test_management -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | xargs)
        echo "Database Tables: $table_count tables found"
    else
        echo -e "Database Connection... ${RED}✗ FAIL${NC}"
        echo "  Tip: Make sure PostgreSQL is running and database is created"
    fi
else
    echo -e "${YELLOW}⚠ psql not found - skipping database check${NC}"
fi
echo ""

# Summary
echo "======================================"
echo "Health check complete!"
echo ""
echo "Next steps:"
echo "  1. All green? Open http://localhost:3000 and test the UI"
echo "  2. Any red? Check START.md for troubleshooting"
echo "  3. View service logs with: docker-compose logs -f"
echo ""
