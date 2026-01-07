#!/bin/bash
# setup-redpanda-docker.sh
# Start Redpanda Docker container for local event streaming
# Usage: ./infrastructure/scripts/setup-redpanda-docker.sh [--force-recreate] [--help]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="redpanda"
REDPANDA_IMAGE="redpandadata/redpanda:latest"
KAFKA_PORT=9092
ADMIN_PORT=9644
SCHEMA_REGISTRY_PORT=8081
FORCE_RECREATE=false

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --force-recreate)
      FORCE_RECREATE=true
      shift
      ;;
    --help)
      echo "Usage: $0 [--force-recreate] [--help]"
      echo ""
      echo "Options:"
      echo "  --force-recreate    Stop and remove existing container, then recreate"
      echo "  --help              Show this help message"
      echo ""
      echo "This script starts a Redpanda Docker container for local development."
      echo "Redpanda is Kafka-compatible and used for event streaming."
      echo ""
      echo "Ports exposed:"
      echo "  9092  - Kafka API (for Dapr Pub/Sub)"
      echo "  9644  - Admin API"
      echo "  8081  - Schema Registry (optional)"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Helper functions
print_step() {
  echo -e "${BLUE}==>${NC} $1"
}

print_success() {
  echo -e "${GREEN}✓${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

# Check Docker is installed
check_docker() {
  print_step "Checking Docker installation..."

  if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo ""
    echo "Please install Docker:"
    echo "  https://docs.docker.com/get-docker/"
    exit 1
  fi

  # Check Docker daemon is running
  if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running"
    echo ""
    echo "Please start Docker and try again"
    exit 1
  fi

  print_success "Docker is installed and running"
}

# Check if port is available
check_port() {
  local port=$1
  if lsof -Pi :$port -sTCP:LISTEN -t &> /dev/null; then
    return 1  # Port is in use
  else
    return 0  # Port is available
  fi
}

# Stop and remove existing container
cleanup_existing_container() {
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    print_warning "Existing Redpanda container found"

    if [ "$FORCE_RECREATE" = true ]; then
      print_step "Stopping and removing existing container..."
      docker stop $CONTAINER_NAME &> /dev/null || true
      docker rm $CONTAINER_NAME &> /dev/null || true
      print_success "Existing container removed"
    else
      # Check if container is already running
      if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_success "Redpanda container is already running"
        return 0
      else
        print_step "Starting existing container..."
        docker start $CONTAINER_NAME
        print_success "Redpanda container started"
        return 0
      fi
    fi
  fi
}

# Check for port conflicts
check_port_conflicts() {
  print_step "Checking for port conflicts..."

  local ports_in_use=()

  if ! check_port $KAFKA_PORT; then
    ports_in_use+=("$KAFKA_PORT (Kafka API)")
  fi

  if ! check_port $ADMIN_PORT; then
    ports_in_use+=("$ADMIN_PORT (Admin API)")
  fi

  if [ ${#ports_in_use[@]} -gt 0 ]; then
    print_error "The following ports are already in use: ${ports_in_use[*]}"
    echo ""
    echo "Please stop any processes using these ports or use --force-recreate to stop existing Redpanda container"
    echo ""
    echo "To find what's using a port:"
    echo "  lsof -i :$KAFKA_PORT"
    exit 1
  fi

  print_success "All required ports are available"
}

# Start Redpanda container
start_redpanda() {
  print_step "Starting Redpanda Docker container..."

  docker run -d \
    --name $CONTAINER_NAME \
    -p $KAFKA_PORT:9092 \
    -p $ADMIN_PORT:9644 \
    $REDPANDA_IMAGE \
    redpanda start \
    --overprovisioned \
    --smp 1 \
    --memory 1G \
    --reserve-memory 0M \
    --node-id 0 \
    --check=false

  print_success "Redpanda container started"
}

# Wait for Redpanda to be ready
wait_for_redpanda() {
  print_step "Waiting for Redpanda to be ready..."

  local max_attempts=30
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    if docker exec $CONTAINER_NAME rpk cluster info &> /dev/null; then
      print_success "Redpanda is ready"
      return 0
    fi

    echo -n "."
    sleep 1
    attempt=$((attempt + 1))
  done

  print_error "Redpanda did not become ready within 30 seconds"
  echo ""
  echo "Check container logs:"
  echo "  docker logs $CONTAINER_NAME"
  exit 1
}

# Create default topics
create_topics() {
  print_step "Creating default topics..."

  # Topics for Phase V
  local topics=(
    "task-events"
    "reminders"
    "task-updates"
  )

  for topic in "${topics[@]}"; do
    # Check if topic already exists
    if docker exec $CONTAINER_NAME rpk topic list | grep -q "^${topic}$"; then
      print_warning "Topic '$topic' already exists, skipping..."
    else
      docker exec $CONTAINER_NAME rpk topic create $topic \
        --partitions 3 \
        --replicas 1
      print_success "Created topic: $topic"
    fi
  done

  print_success "All topics created"
}

# Verify Redpanda is running
verify_redpanda() {
  print_step "Verifying Redpanda installation..."

  # Check cluster info
  print_step "Cluster information:"
  docker exec $CONTAINER_NAME rpk cluster info

  echo ""

  # List topics
  print_step "Topics:"
  docker exec $CONTAINER_NAME rpk topic list

  echo ""

  # Show connection details
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}Redpanda Setup Complete!${NC}"
  echo -e "${GREEN}========================================${NC}"
  echo ""
  echo "Redpanda is running and ready for local development"
  echo ""
  echo "Connection Details:"
  echo -e "  Kafka API:       ${BLUE}localhost:$KAFKA_PORT${NC}"
  echo -e "  Admin API:       ${BLUE}localhost:$ADMIN_PORT${NC}"
  echo ""
  echo "Topics Created:"
  echo "  - task-events     (Task CRUD operations)"
  echo "  - reminders       (Scheduled reminders)"
  echo "  - task-updates    (Real-time WebSocket updates)"
  echo ""
  echo "Useful Commands:"
  echo "  List topics:      docker exec $CONTAINER_NAME rpk topic list"
  echo "  Cluster info:     docker exec $CONTAINER_NAME rpk cluster info"
  echo "  View logs:        docker logs $CONTAINER_NAME -f"
  echo "  Stop container:   docker stop $CONTAINER_NAME"
  echo "  Remove container: docker rm $CONTAINER_NAME"
  echo ""
  echo "Consume events (for debugging):"
  echo "  docker exec $CONTAINER_NAME rpk topic consume task-events"
  echo ""
}

# Main execution
main() {
  echo ""
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}Redpanda Docker Setup${NC}"
  echo -e "${GREEN}Local Event Streaming for Phase V${NC}"
  echo -e "${GREEN}========================================${NC}"
  echo ""

  check_docker
  cleanup_existing_container

  # If container is already running, skip the rest
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    verify_redpanda
    return 0
  fi

  check_port_conflicts
  start_redpanda
  wait_for_redpanda
  create_topics
  verify_redpanda
}

# Run main function
main
