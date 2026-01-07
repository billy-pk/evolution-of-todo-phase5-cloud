#!/bin/bash
# deploy-local.sh
# Deploy Evolution of Todo Phase V to local Minikube with Redpanda Docker
# Usage: ./infrastructure/scripts/deploy-local.sh [--skip-build] [--help]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="default"
HELM_TIMEOUT="5m"
SKIP_BUILD=false

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --help)
      echo "Usage: $0 [--skip-build] [--help]"
      echo ""
      echo "Options:"
      echo "  --skip-build    Skip Docker image builds (use existing images)"
      echo "  --help          Show this help message"
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

# Check prerequisites
check_prerequisites() {
  print_step "Checking prerequisites..."

  local missing_tools=()

  # Check Minikube
  if ! command -v minikube &> /dev/null; then
    missing_tools+=("minikube")
  fi

  # Check kubectl
  if ! command -v kubectl &> /dev/null; then
    missing_tools+=("kubectl")
  fi

  # Check Helm
  if ! command -v helm &> /dev/null; then
    missing_tools+=("helm")
  fi

  # Check Dapr CLI
  if ! command -v dapr &> /dev/null; then
    missing_tools+=("dapr")
  fi

  # Check Docker
  if ! command -v docker &> /dev/null; then
    missing_tools+=("docker")
  fi

  if [ ${#missing_tools[@]} -gt 0 ]; then
    print_error "Missing required tools: ${missing_tools[*]}"
    echo ""
    echo "Please install missing tools:"
    echo "  Minikube: https://minikube.sigs.k8s.io/docs/start/"
    echo "  kubectl: https://kubernetes.io/docs/tasks/tools/"
    echo "  Helm: https://helm.sh/docs/intro/install/"
    echo "  Dapr CLI: https://docs.dapr.io/getting-started/install-dapr-cli/"
    echo "  Docker: https://docs.docker.com/get-docker/"
    exit 1
  fi

  print_success "All prerequisites installed"
}

# Start Minikube if not running
start_minikube() {
  print_step "Checking Minikube status..."

  if minikube status &> /dev/null; then
    print_success "Minikube is already running"
  else
    print_step "Starting Minikube..."
    minikube start --cpus=4 --memory=8192
    print_success "Minikube started"
  fi

  # Get Minikube IP for reference
  MINIKUBE_IP=$(minikube ip)
  print_success "Minikube IP: $MINIKUBE_IP"
}

# Initialize Dapr in Kubernetes
init_dapr() {
  print_step "Checking Dapr installation..."

  if kubectl get namespace dapr-system &> /dev/null; then
    print_success "Dapr is already installed"
  else
    print_step "Installing Dapr to Kubernetes..."
    dapr init -k

    # Wait for Dapr pods to be ready
    print_step "Waiting for Dapr pods to be ready..."
    kubectl wait --for=condition=ready pod --all -n dapr-system --timeout=120s
    print_success "Dapr installed and ready"
  fi
}

# Setup Redpanda Docker
setup_redpanda() {
  print_step "Setting up Redpanda Docker..."

  # Run setup-redpanda-docker.sh script
  if [ -f "infrastructure/scripts/setup-redpanda-docker.sh" ]; then
    bash infrastructure/scripts/setup-redpanda-docker.sh
  else
    print_error "setup-redpanda-docker.sh not found"
    exit 1
  fi
}

# Create Kubernetes secrets
create_secrets() {
  print_step "Checking Kubernetes secrets..."

  # Check if secrets already exist
  if kubectl get secret postgres-credentials &> /dev/null && \
     kubectl get secret openai-credentials &> /dev/null && \
     kubectl get secret better-auth-secret &> /dev/null; then
    print_success "All secrets already exist"
    return
  fi

  # Prompt for missing secrets
  print_warning "Some secrets are missing. You'll need to provide the following:"
  echo ""

  # PostgreSQL credentials
  if ! kubectl get secret postgres-credentials &> /dev/null; then
    echo "Enter PostgreSQL connection string (DATABASE_URL):"
    read -r DATABASE_URL
    kubectl create secret generic postgres-credentials \
      --from-literal=connectionString="$DATABASE_URL"
    print_success "Created postgres-credentials secret"
  fi

  # OpenAI API key
  if ! kubectl get secret openai-credentials &> /dev/null; then
    echo "Enter OpenAI API key:"
    read -rs OPENAI_API_KEY
    echo ""
    kubectl create secret generic openai-credentials \
      --from-literal=apiKey="$OPENAI_API_KEY"
    print_success "Created openai-credentials secret"
  fi

  # Better Auth secret
  if ! kubectl get secret better-auth-secret &> /dev/null; then
    echo "Enter Better Auth secret (min 32 characters):"
    read -rs BETTER_AUTH_SECRET
    echo ""
    kubectl create secret generic better-auth-secret \
      --from-literal=secret="$BETTER_AUTH_SECRET"
    print_success "Created better-auth-secret secret"
  fi
}

# Apply Dapr components
apply_dapr_components() {
  print_step "Applying Dapr components..."

  if [ -d "specs/005-event-driven-microservices/contracts/dapr-components/local" ]; then
    kubectl apply -f specs/005-event-driven-microservices/contracts/dapr-components/local/
    print_success "Dapr components applied"
  else
    print_error "Dapr components directory not found"
    exit 1
  fi
}

# Build Docker images
build_images() {
  if [ "$SKIP_BUILD" = true ]; then
    print_warning "Skipping Docker image builds (--skip-build flag)"
    return
  fi

  print_step "Building Docker images..."

  # Enable Minikube Docker environment
  eval $(minikube docker-env)

  # Build backend image
  print_step "Building backend-api image..."
  docker build -t backend-api:latest ./backend
  print_success "backend-api image built"

  # Build frontend image
  print_step "Building frontend image..."
  docker build -t frontend:latest ./frontend
  print_success "frontend image built"

  # Build microservices images
  print_step "Building notification-service image..."
  docker build -t notification-service:latest ./services/notification-service
  print_success "notification-service image built"

  print_step "Building recurring-task-service image..."
  docker build -t recurring-task-service:latest ./services/recurring-task-service
  print_success "recurring-task-service image built"

  print_step "Building audit-service image..."
  docker build -t audit-service:latest ./services/audit-service
  print_success "audit-service image built"

  print_step "Building websocket-service image..."
  docker build -t websocket-service:latest ./services/websocket-service
  print_success "websocket-service image built"

  print_success "All Docker images built"
}

# Deploy services with Helm
deploy_services() {
  print_step "Deploying services with Helm..."

  # Get secrets for Helm values
  DATABASE_URL=$(kubectl get secret postgres-credentials -o jsonpath='{.data.connectionString}' | base64 -d)
  OPENAI_API_KEY=$(kubectl get secret openai-credentials -o jsonpath='{.data.apiKey}' | base64 -d)
  BETTER_AUTH_SECRET=$(kubectl get secret better-auth-secret -o jsonpath='{.data.secret}' | base64 -d)

  # Deploy Backend API
  print_step "Deploying backend-api..."
  helm upgrade --install backend-api ./infrastructure/helm/backend-api/ \
    -f ./infrastructure/helm/backend-api/values-local.yaml \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    --set-string env.OPENAI_API_KEY="$OPENAI_API_KEY" \
    --set-string env.BETTER_AUTH_SECRET="$BETTER_AUTH_SECRET" \
    --timeout $HELM_TIMEOUT \
    --wait
  print_success "backend-api deployed"

  # Deploy Notification Service
  print_step "Deploying notification-service..."
  helm upgrade --install notification-service ./infrastructure/helm/notification-service/ \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    --timeout $HELM_TIMEOUT \
    --wait
  print_success "notification-service deployed"

  # Deploy Recurring Task Service
  print_step "Deploying recurring-task-service..."
  helm upgrade --install recurring-task-service ./infrastructure/helm/recurring-task-service/ \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    --timeout $HELM_TIMEOUT \
    --wait
  print_success "recurring-task-service deployed"

  # Deploy Audit Service
  print_step "Deploying audit-service..."
  helm upgrade --install audit-service ./infrastructure/helm/audit-service/ \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    --timeout $HELM_TIMEOUT \
    --wait
  print_success "audit-service deployed"

  # Deploy WebSocket Service
  print_step "Deploying websocket-service..."
  helm upgrade --install websocket-service ./infrastructure/helm/websocket-service/ \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    --timeout $HELM_TIMEOUT \
    --wait
  print_success "websocket-service deployed"

  # Deploy Frontend
  print_step "Deploying frontend..."
  helm upgrade --install frontend ./infrastructure/helm/frontend/ \
    -f ./infrastructure/helm/frontend/values-local.yaml \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    --set-string env.BETTER_AUTH_SECRET="$BETTER_AUTH_SECRET" \
    --timeout $HELM_TIMEOUT \
    --wait
  print_success "frontend deployed"

  print_success "All services deployed"
}

# Verify deployment
verify_deployment() {
  print_step "Verifying deployment..."

  # Check all pods are running
  print_step "Checking pod status..."
  kubectl get pods

  # Wait for all pods to be ready
  print_step "Waiting for all pods to be ready..."
  kubectl wait --for=condition=ready pod --all --timeout=300s

  print_success "All pods are ready"

  # Show service URLs
  MINIKUBE_IP=$(minikube ip)
  echo ""
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}Deployment Complete!${NC}"
  echo -e "${GREEN}========================================${NC}"
  echo ""
  echo "Service URLs:"
  echo -e "  Frontend:   ${BLUE}http://$MINIKUBE_IP:30080${NC}"
  echo -e "  Backend:    ${BLUE}http://$MINIKUBE_IP:30081${NC}"
  echo -e "  WebSocket:  ${BLUE}ws://$MINIKUBE_IP:30082${NC}"
  echo ""
  echo "Next Steps:"
  echo "  1. Open http://$MINIKUBE_IP:30080 in your browser"
  echo "  2. Sign up or sign in to the application"
  echo "  3. Navigate to /chat to test the conversational interface"
  echo "  4. Follow the test scenarios in specs/005-event-driven-microservices/quickstart.md"
  echo ""
  echo "Useful Commands:"
  echo "  View logs:        kubectl logs -l app=<service-name> --tail=100 -f"
  echo "  View pods:        kubectl get pods"
  echo "  Dapr dashboard:   dapr dashboard -k"
  echo "  Teardown:         ./infrastructure/scripts/teardown.sh"
  echo ""
}

# Main execution
main() {
  echo ""
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}Evolution of Todo - Phase V${NC}"
  echo -e "${GREEN}Local Deployment to Minikube${NC}"
  echo -e "${GREEN}========================================${NC}"
  echo ""

  check_prerequisites
  start_minikube
  init_dapr
  setup_redpanda
  create_secrets
  apply_dapr_components
  build_images
  deploy_services
  verify_deployment
}

# Run main function
main
