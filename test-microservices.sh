#!/bin/bash
#
# Microservices Health Check Script
# Tests all microservices in the Evolution of Todo Phase 5 deployment
#
# Usage: ./test-microservices.sh
#

set -e

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to print test results
print_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ $2 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $1"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for pod to be ready
wait_for_pod() {
    local pod_label=$1
    local timeout=30
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if kubectl get pods -l "$pod_label" -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q "Running"; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    return 1
}

print_section "1. PREREQUISITE CHECKS"

# Check if kubectl is installed
if command_exists kubectl; then
    print_test "kubectl installed" 0
else
    print_test "kubectl installed" 1
    echo -e "${RED}Error: kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

# Check if minikube is running
if minikube status | grep -q "Running"; then
    print_test "Minikube running" 0
else
    print_test "Minikube running" 1
    echo -e "${RED}Error: Minikube not running. Start with 'minikube start'${NC}"
    exit 1
fi

print_section "2. POD STATUS CHECKS"

# Check each microservice pod
SERVICES=(
    "app.kubernetes.io/name=backend-api:Backend API"
    "app.kubernetes.io/name=frontend:Frontend"
    "app.kubernetes.io/name=mcp-server:MCP Server"
    "app.kubernetes.io/name=audit-service:Audit Service"
    "app.kubernetes.io/name=notification-service:Notification Service"
    "app.kubernetes.io/name=recurring-task-service:Recurring Task Service"
    "app.kubernetes.io/name=websocket-service:WebSocket Service"
)

for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r label name <<< "$service_info"

    # Check if pod exists and is running
    POD_STATUS=$(kubectl get pods -l "$label" -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    if [ "$POD_STATUS" = "Running" ]; then
        # Check if all containers are ready
        READY=$(kubectl get pods -l "$label" -o jsonpath='{.items[0].status.containerStatuses[*].ready}' 2>/dev/null)
        if echo "$READY" | grep -q "false"; then
            print_test "$name pod running (some containers not ready)" 1
        else
            print_test "$name pod running and ready" 0
        fi
    else
        print_test "$name pod running" 1
    fi
done

# Check Redpanda pod
REDPANDA_POD=$(kubectl get pods -l app=redpanda -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$REDPANDA_POD" ] && kubectl get pod "$REDPANDA_POD" -o jsonpath='{.status.phase}' | grep -q "Running"; then
    print_test "Redpanda pod running" 0
else
    print_test "Redpanda pod running" 1
fi

print_section "3. KUBERNETES SERVICES"

# Check if services are exposed
KUBE_SERVICES=(
    "backend-api"
    "frontend"
    "mcp-server"
    "audit-service"
    "notification-service"
    "recurring-task-service"
    "websocket-service"
    "redpanda"
)

for svc in "${KUBE_SERVICES[@]}"; do
    if kubectl get svc "$svc" >/dev/null 2>&1; then
        CLUSTER_IP=$(kubectl get svc "$svc" -o jsonpath='{.spec.clusterIP}')
        print_test "$svc service exists (ClusterIP: $CLUSTER_IP)" 0
    else
        print_test "$svc service exists" 1
    fi
done

print_section "4. DAPR COMPONENTS"

# Check Dapr sidecars
DAPR_SERVICES=(
    "backend-api"
    "mcp-server"
    "audit-service"
    "notification-service"
    "recurring-task-service"
    "websocket-service"
)

for svc in "${DAPR_SERVICES[@]}"; do
    POD=$(kubectl get pods -l "app.kubernetes.io/name=$svc" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$POD" ]; then
        # Check if daprd container exists
        if kubectl get pod "$POD" -o jsonpath='{.spec.containers[*].name}' | grep -q "daprd"; then
            print_test "$svc Dapr sidecar injected" 0
        else
            print_test "$svc Dapr sidecar injected" 1
        fi
    fi
done

# Check Dapr components
if kubectl get components -n default >/dev/null 2>&1; then
    COMPONENT_COUNT=$(kubectl get components -n default --no-headers 2>/dev/null | wc -l)
    if [ "$COMPONENT_COUNT" -gt 0 ]; then
        print_test "Dapr components configured ($COMPONENT_COUNT components)" 0
    else
        print_test "Dapr components configured" 1
    fi
else
    print_test "Dapr components configured" 1
fi

print_section "5. PORT FORWARDING STATUS"

# Check if port-forwards are running
PORT_FORWARDS=(
    "3000:Frontend"
    "8000:Backend API"
    "8005:WebSocket Service"
)

for pf_info in "${PORT_FORWARDS[@]}"; do
    IFS=':' read -r port name <<< "$pf_info"
    if ps aux | grep "port-forward" | grep -q "$port:$port"; then
        print_test "$name port-forward active (localhost:$port)" 0
    else
        print_test "$name port-forward active (localhost:$port)" 1
        echo -e "${YELLOW}  → Start with: kubectl port-forward svc/${name,,} $port:$port &${NC}"
    fi
done

print_section "6. HEALTH ENDPOINT CHECKS"

# Check backend API health endpoint
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null)
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        print_test "Backend API health endpoint responding" 0
    else
        print_test "Backend API health endpoint responding (unhealthy)" 1
    fi
else
    print_test "Backend API health endpoint accessible" 1
fi

# Check frontend accessibility
if curl -s -f http://localhost:3000 >/dev/null 2>&1; then
    print_test "Frontend accessible" 0
else
    print_test "Frontend accessible" 1
fi

# Check WebSocket service
if curl -s -f http://localhost:8005/health >/dev/null 2>&1; then
    print_test "WebSocket service health endpoint responding" 0
else
    print_test "WebSocket service health endpoint accessible" 1
fi

print_section "7. REDPANDA/KAFKA CONNECTIVITY"

# Check if Redpanda service is accessible from within cluster
if [ -n "$REDPANDA_POD" ]; then
    # Test Redpanda broker connectivity
    if kubectl exec "$REDPANDA_POD" -- rpk cluster info >/dev/null 2>&1; then
        print_test "Redpanda broker accessible" 0
    else
        print_test "Redpanda broker accessible" 1
    fi

    # List topics
    TOPICS=$(kubectl exec "$REDPANDA_POD" -- rpk topic list 2>/dev/null | grep -v "NAME" | wc -l)
    if [ "$TOPICS" -gt 0 ]; then
        print_test "Redpanda topics configured ($TOPICS topics)" 0
    else
        print_test "Redpanda topics configured" 1
        echo -e "${YELLOW}  → Topics may need to be created${NC}"
    fi
else
    print_test "Redpanda pod available for testing" 1
fi

print_section "8. DATABASE CONNECTIVITY"

# Test database connection from backend pod
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
    exit(1)
" >/dev/null 2>&1; then
        print_test "Backend can connect to PostgreSQL" 0
    else
        print_test "Backend can connect to PostgreSQL" 1
    fi
fi

print_section "9. EVENT FLOW TEST (Optional)"

echo -e "${YELLOW}To test event flow between microservices:${NC}"
echo "1. Create a task via chat or API"
echo "2. Check audit service logs: kubectl logs -l app.kubernetes.io/name=audit-service -c audit-service --tail=20"
echo "3. Check notification service logs: kubectl logs -l app.kubernetes.io/name=notification-service -c notification-service --tail=20"
echo ""
echo -e "${YELLOW}Run event flow test? (y/n)${NC}"
read -r RUN_EVENT_TEST

if [ "$RUN_EVENT_TEST" = "y" ] || [ "$RUN_EVENT_TEST" = "Y" ]; then
    echo "Creating test task via backend API..."

    # Get user token (this would need to be customized based on your auth setup)
    TEST_RESPONSE=$(curl -s -X POST http://localhost:8000/api/test-user-id/tasks \
        -H "Content-Type: application/json" \
        -d '{"title":"Test Microservices Event Flow","description":"Auto-generated test task"}' 2>/dev/null)

    if echo "$TEST_RESPONSE" | grep -q "success\|id"; then
        print_test "Test task created via API" 0
        echo "Waiting for event propagation (5 seconds)..."
        sleep 5

        # Check audit service received event
        AUDIT_LOGS=$(kubectl logs -l app.kubernetes.io/name=audit-service -c audit-service --tail=20 2>/dev/null)
        if echo "$AUDIT_LOGS" | grep -q "task.created\|Test Microservices"; then
            print_test "Audit service received task.created event" 0
        else
            print_test "Audit service received task.created event" 1
        fi
    else
        print_test "Test task created via API" 1
        echo -e "${YELLOW}  → May need valid JWT token for authentication${NC}"
    fi
fi

print_section "SUMMARY"

echo ""
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All microservices are healthy!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed. Check the output above for details.${NC}"
    echo ""
    echo -e "${YELLOW}Common fixes:${NC}"
    echo "- Restart failed pods: kubectl rollout restart deployment <service-name>"
    echo "- Check pod logs: kubectl logs -l app.kubernetes.io/name=<service-name> --tail=50"
    echo "- Verify secrets: kubectl get secrets"
    echo "- Check Dapr logs: kubectl logs <pod-name> -c daprd"
    exit 1
fi
