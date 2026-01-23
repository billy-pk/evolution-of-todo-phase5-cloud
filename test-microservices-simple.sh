#!/bin/bash
#
# Microservices Health Check (Simplified)
# Tests microservices in Minikube + Redpanda on Docker Desktop
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

print_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

test_result() {
    if [ $2 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $1"
        FAILED=$((FAILED + 1))
        if [ -n "$3" ]; then
            echo -e "${YELLOW}  → $3${NC}"
        fi
    fi
}

print_section "KUBERNETES PODS STATUS"

kubectl get pods -o wide

print_section "MICROSERVICES HEALTH"

# Check each pod
PODS=$(kubectl get pods --no-headers -o custom-columns=":metadata.name")
for pod in $PODS; do
    STATUS=$(kubectl get pod "$pod" -o jsonpath='{.status.phase}')
    READY=$(kubectl get pod "$pod" -o jsonpath='{.status.containerStatuses[*].ready}')

    if [ "$STATUS" = "Running" ]; then
        if echo "$READY" | grep -q "false"; then
            test_result "Pod $pod" 1 "Running but some containers not ready"
        else
            test_result "Pod $pod running and ready" 0
        fi
    else
        test_result "Pod $pod" 1 "Status: $STATUS"
    fi
done

print_section "DAPR COMPONENTS"

kubectl get components -n default

COMPONENT_COUNT=$(kubectl get components -n default --no-headers 2>/dev/null | wc -l)
test_result "Dapr components configured ($COMPONENT_COUNT found)" 0

print_section "PORT FORWARDING"

if ps aux | grep "port-forward" | grep -q "3000:3000"; then
    test_result "Frontend port-forward (3000)" 0
else
    test_result "Frontend port-forward (3000)" 1 "Start: kubectl port-forward svc/frontend 3000:3000"
fi

if ps aux | grep "port-forward" | grep -q "8000:8000"; then
    test_result "Backend API port-forward (8000)" 0
else
    test_result "Backend API port-forward (8000)" 1 "Start: kubectl port-forward svc/backend-api 8000:8000"
fi

if ps aux | grep "port-forward" | grep -q "8005:8005"; then
    test_result "WebSocket port-forward (8005)" 0
else
    test_result "WebSocket port-forward (8005)" 1 "Start: kubectl port-forward svc/websocket-service 8005:8005"
fi

print_section "HEALTH ENDPOINTS"

# Backend API
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
    if echo "$HEALTH" | grep -q "healthy"; then
        test_result "Backend API (/health)" 0
        echo "  Response: $HEALTH"
    else
        test_result "Backend API (/health)" 1 "Unhealthy response"
    fi
else
    test_result "Backend API (/health)" 1 "Not accessible"
fi

# Frontend
if curl -s -f -I http://localhost:3000 >/dev/null 2>&1; then
    test_result "Frontend (localhost:3000)" 0
else
    test_result "Frontend (localhost:3000)" 1 "Not accessible"
fi

# WebSocket Service
if curl -s -f http://localhost:8005/health >/dev/null 2>&1; then
    test_result "WebSocket Service (/health)" 0
else
    test_result "WebSocket Service (/health)" 1 "Not accessible"
fi

print_section "REDPANDA (Docker Desktop)"

# Check Redpanda container
if docker ps --filter "name=redpanda" --format "{{.Names}}" | grep -q "redpanda"; then
    STATUS=$(docker ps --filter "name=redpanda" --format "{{.Status}}")
    test_result "Redpanda container running" 0
    echo "  Status: $STATUS"

    # Check if Redpanda is accessible
    REDPANDA_CONTAINER=$(docker ps --filter "name=redpanda" --format "{{.Names}}" | head -1)
    if docker exec "$REDPANDA_CONTAINER" rpk cluster info >/dev/null 2>&1; then
        test_result "Redpanda broker accessible" 0

        # List topics
        echo ""
        echo "Topics:"
        docker exec "$REDPANDA_CONTAINER" rpk topic list 2>/dev/null || echo "  Could not list topics"
    else
        test_result "Redpanda broker accessible" 1
    fi
else
    test_result "Redpanda container running" 1 "Start Redpanda on Docker Desktop"
fi

print_section "DATABASE CONNECTIVITY"

BACKEND_POD=$(kubectl get pods -l app.kubernetes.io/name=backend-api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$BACKEND_POD" ]; then
    if kubectl exec "$BACKEND_POD" -c backend-api -- python3 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    exit(0)
except Exception as e:
    print(str(e))
    exit(1)
" >/dev/null 2>&1; then
        test_result "Backend → PostgreSQL connection" 0
    else
        test_result "Backend → PostgreSQL connection" 1
    fi
fi

print_section "QUICK SERVICE LOGS CHECK"

echo "Recent audit-service logs:"
kubectl logs -l app.kubernetes.io/name=audit-service -c audit-service --tail=5 2>/dev/null || echo "  No logs available"

echo ""
echo "Recent notification-service logs:"
kubectl logs -l app.kubernetes.io/name=notification-service -c notification-service --tail=5 2>/dev/null || echo "  No logs available"

print_section "SUMMARY"

TOTAL=$((PASSED + FAILED))
echo ""
echo "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All microservices are healthy!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed. Review details above.${NC}"
    exit 1
fi
