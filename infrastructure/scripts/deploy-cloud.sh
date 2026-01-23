#!/bin/bash
# deploy-cloud.sh
# Deploy Evolution of Todo Phase V to Oracle Kubernetes Engine (OKE) with Redpanda Cloud
# Usage: ./infrastructure/scripts/deploy-cloud.sh [--dry-run] [--help]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="default"
HELM_TIMEOUT="10m"
DRY_RUN=false

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --help)
      echo "Usage: $0 [--dry-run] [--help]"
      echo ""
      echo "Options:"
      echo "  --dry-run       Show what would be deployed without actually deploying"
      echo "  --help          Show this help message"
      echo ""
      echo "Environment Variables Required:"
      echo "  KUBECONFIG                - Path to Kubernetes config for OKE cluster"
      echo "  DATABASE_URL              - PostgreSQL connection string (Neon)"
      echo "  OPENAI_API_KEY            - OpenAI API key"
      echo "  BETTER_AUTH_SECRET        - Better Auth shared secret (min 32 chars)"
      echo "  REDPANDA_BROKERS          - Redpanda Cloud broker addresses (e.g., 'broker1:9092,broker2:9092')"
      echo "  REDPANDA_SASL_USERNAME    - Redpanda Cloud SASL username"
      echo "  REDPANDA_SASL_PASSWORD    - Redpanda Cloud SASL password"
      echo "  FRONTEND_URL              - Public frontend URL (e.g., 'https://todo.example.com')"
      echo "  BACKEND_URL               - Public backend URL (e.g., 'https://api.todo.example.com')"
      echo ""
      echo "Example:"
      echo "  export KUBECONFIG=~/.kube/oke-config"
      echo "  export DATABASE_URL='postgresql://user:pass@host/db'"
      echo "  export OPENAI_API_KEY='sk-...'"
      echo "  export BETTER_AUTH_SECRET='your-secret-32-chars-min'"
      echo "  export REDPANDA_BROKERS='broker.redpanda.cloud:9092'"
      echo "  export REDPANDA_SASL_USERNAME='your-username'"
      echo "  export REDPANDA_SASL_PASSWORD='your-password'"
      echo "  export FRONTEND_URL='https://todo.example.com'"
      echo "  export BACKEND_URL='https://api.todo.example.com'"
      echo "  ./infrastructure/scripts/deploy-cloud.sh"
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

  if [ ${#missing_tools[@]} -gt 0 ]; then
    print_error "Missing required tools: ${missing_tools[*]}"
    echo ""
    echo "Please install missing tools:"
    echo "  kubectl: https://kubernetes.io/docs/tasks/tools/"
    echo "  Helm: https://helm.sh/docs/intro/install/"
    echo "  Dapr CLI: https://docs.dapr.io/getting-started/install-dapr-cli/"
    exit 1
  fi

  print_success "All prerequisites installed"
}

# Validate environment variables
validate_environment() {
  print_step "Validating environment variables..."

  local missing_vars=()

  # Check required environment variables
  [ -z "$KUBECONFIG" ] && missing_vars+=("KUBECONFIG")
  [ -z "$DATABASE_URL" ] && missing_vars+=("DATABASE_URL")
  [ -z "$OPENAI_API_KEY" ] && missing_vars+=("OPENAI_API_KEY")
  [ -z "$BETTER_AUTH_SECRET" ] && missing_vars+=("BETTER_AUTH_SECRET")
  [ -z "$REDPANDA_BROKERS" ] && missing_vars+=("REDPANDA_BROKERS")
  [ -z "$REDPANDA_SASL_USERNAME" ] && missing_vars+=("REDPANDA_SASL_USERNAME")
  [ -z "$REDPANDA_SASL_PASSWORD" ] && missing_vars+=("REDPANDA_SASL_PASSWORD")
  [ -z "$FRONTEND_URL" ] && missing_vars+=("FRONTEND_URL")
  [ -z "$BACKEND_URL" ] && missing_vars+=("BACKEND_URL")

  if [ ${#missing_vars[@]} -gt 0 ]; then
    print_error "Missing required environment variables: ${missing_vars[*]}"
    echo ""
    echo "Use --help to see required environment variables and examples"
    exit 1
  fi

  # Validate Better Auth secret length
  if [ ${#BETTER_AUTH_SECRET} -lt 32 ]; then
    print_error "BETTER_AUTH_SECRET must be at least 32 characters"
    exit 1
  fi

  print_success "All environment variables validated"
}

# Verify Kubernetes connection
verify_kubernetes_connection() {
  print_step "Verifying Kubernetes connection..."

  if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    echo ""
    echo "Please check:"
    echo "  1. KUBECONFIG is set correctly"
    echo "  2. Kubernetes cluster is accessible"
    echo "  3. kubectl can authenticate to the cluster"
    exit 1
  fi

  CLUSTER_NAME=$(kubectl config current-context)
  print_success "Connected to cluster: $CLUSTER_NAME"
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
    kubectl wait --for=condition=ready pod --all -n dapr-system --timeout=300s
    print_success "Dapr installed and ready"
  fi
}

# Create Kubernetes secrets
create_secrets() {
  print_step "Creating Kubernetes secrets..."

  # PostgreSQL credentials
  if kubectl get secret postgres-credentials &> /dev/null; then
    print_warning "postgres-credentials secret already exists, updating..."
    kubectl delete secret postgres-credentials
  fi
  kubectl create secret generic postgres-credentials \
    --from-literal=connectionString="$DATABASE_URL"
  print_success "Created postgres-credentials secret"

  # OpenAI API key
  if kubectl get secret openai-credentials &> /dev/null; then
    print_warning "openai-credentials secret already exists, updating..."
    kubectl delete secret openai-credentials
  fi
  kubectl create secret generic openai-credentials \
    --from-literal=apiKey="$OPENAI_API_KEY"
  print_success "Created openai-credentials secret"

  # Better Auth secret
  if kubectl get secret better-auth-secret &> /dev/null; then
    print_warning "better-auth-secret already exists, updating..."
    kubectl delete secret better-auth-secret
  fi
  kubectl create secret generic better-auth-secret \
    --from-literal=secret="$BETTER_AUTH_SECRET"
  print_success "Created better-auth-secret secret"

  # Redpanda Cloud credentials
  if kubectl get secret redpanda-credentials &> /dev/null; then
    print_warning "redpanda-credentials secret already exists, updating..."
    kubectl delete secret redpanda-credentials
  fi
  kubectl create secret generic redpanda-credentials \
    --from-literal=brokers="$REDPANDA_BROKERS" \
    --from-literal=saslUsername="$REDPANDA_SASL_USERNAME" \
    --from-literal=saslPassword="$REDPANDA_SASL_PASSWORD"
  print_success "Created redpanda-credentials secret"
}

# Apply Dapr components
apply_dapr_components() {
  print_step "Applying Dapr components for cloud..."

  if [ -d "specs/005-event-driven-microservices/contracts/dapr-components/cloud" ]; then
    kubectl apply -f specs/005-event-driven-microservices/contracts/dapr-components/cloud/
    print_success "Dapr components applied"
  else
    print_error "Cloud Dapr components directory not found"
    exit 1
  fi
}

# Deploy services with Helm
deploy_services() {
  print_step "Deploying services with Helm..."

  local helm_flags="--timeout $HELM_TIMEOUT --wait"
  if [ "$DRY_RUN" = true ]; then
    helm_flags="$helm_flags --dry-run"
    print_warning "DRY RUN MODE - No actual deployment will occur"
  fi

  # Deploy MCP Server (internal ClusterIP service - must be deployed before backend-api)
  print_step "Deploying mcp-server..."
  helm upgrade --install mcp-server ./infrastructure/helm/mcp-server/ \
    -f ./infrastructure/helm/mcp-server/values-cloud.yaml \
    $helm_flags
  print_success "mcp-server deployed"

  # Deploy Backend API
  print_step "Deploying backend-api..."
  helm upgrade --install backend-api ./infrastructure/helm/backend-api/ \
    -f ./infrastructure/helm/backend-api/values-cloud.yaml \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    --set-string env.OPENAI_API_KEY="$OPENAI_API_KEY" \
    --set-string env.BETTER_AUTH_SECRET="$BETTER_AUTH_SECRET" \
    --set-string env.BETTER_AUTH_ISSUER="$FRONTEND_URL" \
    --set-string env.BETTER_AUTH_JWKS_URL="$FRONTEND_URL/api/auth/jwks" \
    $helm_flags
  print_success "backend-api deployed"

  # Deploy Notification Service
  print_step "Deploying notification-service..."
  helm upgrade --install notification-service ./infrastructure/helm/notification-service/ \
    -f ./infrastructure/helm/notification-service/values-cloud.yaml \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    $helm_flags
  print_success "notification-service deployed"

  # Deploy Recurring Task Service
  print_step "Deploying recurring-task-service..."
  helm upgrade --install recurring-task-service ./infrastructure/helm/recurring-task-service/ \
    -f ./infrastructure/helm/recurring-task-service/values-cloud.yaml \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    $helm_flags
  print_success "recurring-task-service deployed"

  # Deploy Audit Service
  print_step "Deploying audit-service..."
  helm upgrade --install audit-service ./infrastructure/helm/audit-service/ \
    -f ./infrastructure/helm/audit-service/values-cloud.yaml \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    $helm_flags
  print_success "audit-service deployed"

  # Deploy WebSocket Service
  print_step "Deploying websocket-service..."
  helm upgrade --install websocket-service ./infrastructure/helm/websocket-service/ \
    -f ./infrastructure/helm/websocket-service/values-cloud.yaml \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    $helm_flags
  print_success "websocket-service deployed"

  # Deploy Frontend
  print_step "Deploying frontend..."
  helm upgrade --install frontend ./infrastructure/helm/frontend/ \
    -f ./infrastructure/helm/frontend/values-cloud.yaml \
    --set-string env.DATABASE_URL="$DATABASE_URL" \
    --set-string env.BETTER_AUTH_SECRET="$BETTER_AUTH_SECRET" \
    --set-string env.BETTER_AUTH_URL="$FRONTEND_URL" \
    --set-string env.NEXT_PUBLIC_API_URL="$BACKEND_URL" \
    $helm_flags
  print_success "frontend deployed"

  print_success "All services deployed"
}

# Verify deployment
verify_deployment() {
  if [ "$DRY_RUN" = true ]; then
    print_warning "Skipping verification (dry-run mode)"
    return
  fi

  print_step "Verifying deployment..."

  # Check all pods are running
  print_step "Checking pod status..."
  kubectl get pods

  # Wait for all pods to be ready
  print_step "Waiting for all pods to be ready..."
  kubectl wait --for=condition=ready pod --all --timeout=600s

  print_success "All pods are ready"

  # Show deployment summary
  echo ""
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}Cloud Deployment Complete!${NC}"
  echo -e "${GREEN}========================================${NC}"
  echo ""
  echo "Service URLs:"
  echo -e "  Frontend:   ${BLUE}$FRONTEND_URL${NC}"
  echo -e "  Backend:    ${BLUE}$BACKEND_URL${NC}"
  echo ""
  echo "Next Steps:"
  echo "  1. Verify DNS records point to the load balancer IPs"
  echo "  2. Configure SSL/TLS certificates (if not already done)"
  echo "  3. Open $FRONTEND_URL in your browser"
  echo "  4. Sign up or sign in to the application"
  echo "  5. Navigate to /chat to test the conversational interface"
  echo ""
  echo "Useful Commands:"
  echo "  View logs:        kubectl logs -l app=<service-name> --tail=100 -f"
  echo "  View pods:        kubectl get pods"
  echo "  View services:    kubectl get svc"
  echo "  Dapr components:  dapr components -k"
  echo "  Teardown:         ./infrastructure/scripts/teardown.sh"
  echo ""
}

# Main execution
main() {
  echo ""
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}Evolution of Todo - Phase V${NC}"
  echo -e "${GREEN}Cloud Deployment to OKE${NC}"
  echo -e "${GREEN}========================================${NC}"
  echo ""

  check_prerequisites
  validate_environment
  verify_kubernetes_connection
  init_dapr
  create_secrets
  apply_dapr_components
  deploy_services
  verify_deployment
}

# Run main function
main
