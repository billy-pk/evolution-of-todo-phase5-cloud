#!/bin/bash
#
# Event Flow Test - Verify pub/sub communication between microservices
# Tests that events published by backend reach audit and notification services
#

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}EVENT FLOW TEST${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get backend pod name
BACKEND_POD=$(kubectl get pods -l app.kubernetes.io/name=backend-api -o jsonpath='{.items[0].metadata.name}')
AUDIT_POD=$(kubectl get pods -l app.kubernetes.io/name=audit-service -o jsonpath='{.items[0].metadata.name}')
NOTIFICATION_POD=$(kubectl get pods -l app.kubernetes.io/name=notification-service -o jsonpath='{.items[0].metadata.name}')

echo "Backend Pod: $BACKEND_POD"
echo "Audit Pod: $AUDIT_POD"
echo "Notification Pod: $NOTIFICATION_POD"
echo ""

# Clear recent logs by getting current timestamp
echo "Capturing baseline..."
sleep 2

# Test 1: Check if services can publish to Dapr
echo -e "${YELLOW}Test 1: Dapr Pub/Sub Connectivity${NC}"

# Check if backend has Dapr sidecar
if kubectl logs "$BACKEND_POD" -c daprd --tail=5 >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend has Dapr sidecar"
else
    echo -e "${RED}✗${NC} Backend missing Dapr sidecar"
fi

if kubectl logs "$AUDIT_POD" -c daprd --tail=5 >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Audit service has Dapr sidecar"
else
    echo -e "${RED}✗${NC} Audit service missing Dapr sidecar"
fi

if kubectl logs "$NOTIFICATION_POD" -c daprd --tail=5 >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Notification service has Dapr sidecar"
else
    echo -e "${RED}✗${NC} Notification service missing Dapr sidecar"
fi

echo ""

# Test 2: Check Redpanda topics from Minikube pods
echo -e "${YELLOW}Test 2: Redpanda Topic Accessibility${NC}"

# Check if backend can reach Redpanda (via host.minikube.internal)
# This would require the pods to have network access to Docker Desktop

echo "Testing Redpanda connectivity from backend pod..."
if kubectl exec "$BACKEND_POD" -c backend-api -- timeout 5 nc -zv host.minikube.internal 9092 2>&1 | grep -q "succeeded"; then
    echo -e "${GREEN}✓${NC} Backend can reach Redpanda on Docker Desktop"
else
    echo -e "${YELLOW}⚠${NC} Backend cannot reach Redpanda directly (expected if using Dapr)"
fi

echo ""

# Test 3: Check Dapr subscriptions
echo -e "${YELLOW}Test 3: Dapr Subscriptions${NC}"

echo "Checking audit service subscriptions..."
AUDIT_SUBSCRIPTIONS=$(kubectl logs "$AUDIT_POD" -c daprd --tail=100 2>/dev/null | grep -i "subscription" | tail -3)
if [ -n "$AUDIT_SUBSCRIPTIONS" ]; then
    echo -e "${GREEN}✓${NC} Audit service has Dapr subscriptions configured"
else
    echo -e "${YELLOW}⚠${NC} No subscription logs found (may be normal if already initialized)"
fi

echo ""

# Test 4: Simulate task creation and monitor event flow
echo -e "${YELLOW}Test 4: End-to-End Event Flow${NC}"
echo "This test creates a task and monitors event propagation"
echo ""

read -p "Create a test task and monitor events? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    TASK_TITLE="E2E-Test-$(date +%s)"

    echo "Creating task via backend API..."
    echo "Task title: $TASK_TITLE"

    # Note: This requires authentication token
    # For testing, you can create task directly in database
    echo ""
    echo -e "${YELLOW}Creating task directly in database for testing...${NC}"

    kubectl exec "$BACKEND_POD" -c backend-api -- python3 <<EOF
import os
import sys
from sqlmodel import Session, create_engine, select
from datetime import datetime, UTC
from models import Task
import uuid

try:
    engine = create_engine(os.getenv('DATABASE_URL'))
    with Session(engine) as session:
        task = Task(
            id=str(uuid.uuid4()),
            user_id="test-user-e2e",
            title="$TASK_TITLE",
            description="Auto-generated for event flow testing",
            completed=False,
            created_at=datetime.now(UTC)
        )
        session.add(task)
        session.commit()
        print(f"✓ Created task: {task.id}")
        print(f"  Title: {task.title}")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Task created successfully"

        echo ""
        echo "Waiting for event propagation (5 seconds)..."
        sleep 5

        echo ""
        echo "Checking audit service logs..."
        AUDIT_LOGS=$(kubectl logs "$AUDIT_POD" -c audit-service --tail=20 2>/dev/null | grep -i "$TASK_TITLE\|task.created" | head -5)
        if [ -n "$AUDIT_LOGS" ]; then
            echo -e "${GREEN}✓${NC} Event reached audit service"
            echo "$AUDIT_LOGS"
        else
            echo -e "${YELLOW}⚠${NC} Event not found in audit logs (check Dapr pub/sub)"
        fi

        echo ""
        echo "Checking notification service logs..."
        NOTIF_LOGS=$(kubectl logs "$NOTIFICATION_POD" -c notification-service --tail=20 2>/dev/null | grep -i "$TASK_TITLE\|task.created" | head -5)
        if [ -n "$NOTIF_LOGS" ]; then
            echo -e "${GREEN}✓${NC} Event reached notification service"
            echo "$NOTIF_LOGS"
        else
            echo -e "${YELLOW}⚠${NC} Event not found in notification logs"
        fi

        echo ""
        echo "Checking backend Dapr sidecar publish logs..."
        BACKEND_DAPR=$(kubectl logs "$BACKEND_POD" -c daprd --tail=50 2>/dev/null | grep -i "publish" | tail -5)
        if [ -n "$BACKEND_DAPR" ]; then
            echo "Recent publish activity:"
            echo "$BACKEND_DAPR"
        fi

    else
        echo -e "${RED}✗${NC} Failed to create test task"
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DIAGNOSTIC COMMANDS${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "View live audit service logs:"
echo "  kubectl logs -f $AUDIT_POD -c audit-service"
echo ""
echo "View live notification service logs:"
echo "  kubectl logs -f $NOTIFICATION_POD -c notification-service"
echo ""
echo "View backend Dapr sidecar:"
echo "  kubectl logs $BACKEND_POD -c daprd --tail=50"
echo ""
echo "Check Redpanda topics:"
echo "  docker exec redpanda rpk topic list"
echo ""
echo "Consume from task-events topic:"
echo "  docker exec redpanda rpk topic consume task-events --num 10"
echo ""
