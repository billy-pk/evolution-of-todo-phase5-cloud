#!/bin/bash
# teardown.sh
# Clean up all Evolution of Todo Phase V resources
# Usage: ./infrastructure/scripts/teardown.sh [--local|--cloud] [--keep-secrets] [--help]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="auto"  # auto, local, cloud
KEEP_SECRETS=false

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --local)
      ENVIRONMENT="local"
      shift
      ;;
    --cloud)
      ENVIRONMENT="cloud"
      shift
      ;;
    --keep-secrets)
      KEEP_SECRETS=true
      shift
      ;;
    --help)
      echo "Usage: $0 [--local|--cloud] [--keep-secrets] [--help]"
      echo ""
      echo "Options:"
      echo "  --local         Teardown local Minikube deployment (stop Minikube, Redpanda)"
      echo "  --cloud         Teardown cloud OKE deployment (keep cluster running)"
      echo "  --keep-secrets  Don't delete Kubernetes secrets"
      echo "  --help          Show this help message"
      echo ""
      echo "If no environment is specified, auto-detect based on current kubectl context"
      echo ""
      echo "Examples:"
      echo "  ./infrastructure/scripts/teardown.sh --local"
      echo "  ./infrastructure/scripts/teardown.sh --cloud --keep-secrets"
      echo "  ./infrastructure/scripts/teardown.sh  # Auto-detect environment"
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

# Detect environment
detect_environment() {
  if [ "$ENVIRONMENT" != "auto" ]; then
    return
  fi

  print_step "Detecting environment..."

  if ! command -v kubectl &> /dev/null; then
    print_error "kubectl not found, cannot detect environment"
    exit 1
  fi

  # Check current context
  CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "none")

  if [[ "$CURRENT_CONTEXT" == *"minikube"* ]]; then
    ENVIRONMENT="local"
    print_success "Detected local Minikube environment"
  else
    ENVIRONMENT="cloud"
    print_success "Detected cloud environment: $CURRENT_CONTEXT"
  fi
}

# Confirm teardown
confirm_teardown() {
  echo ""
  echo -e "${YELLOW}========================================${NC}"
  echo -e "${YELLOW}WARNING: Teardown Confirmation${NC}"
  echo -e "${YELLOW}========================================${NC}"
  echo ""
  echo "This will remove the following resources:"
  echo "  - All Helm releases (backend-api, frontend, microservices)"
  echo "  - Dapr components"

  if [ "$KEEP_SECRETS" = false ]; then
    echo "  - Kubernetes secrets (DATABASE_URL, API keys)"
  fi

  if [ "$ENVIRONMENT" = "local" ]; then
    echo "  - Redpanda Docker container"
    echo "  - Minikube cluster"
  fi

  echo ""
  read -p "Are you sure you want to proceed? (yes/no): " -r
  echo ""

  if [[ ! $REPLY =~ ^[Yy](es)?$ ]]; then
    print_warning "Teardown cancelled"
    exit 0
  fi

  print_success "Proceeding with teardown..."
}

# Uninstall Helm releases
uninstall_helm_releases() {
  print_step "Uninstalling Helm releases..."

  local releases=(
    "frontend"
    "websocket-service"
    "audit-service"
    "recurring-task-service"
    "notification-service"
    "backend-api"
  )

  for release in "${releases[@]}"; do
    if helm list | grep -q "^${release}"; then
      print_step "Uninstalling $release..."
      helm uninstall $release --wait &
    else
      print_warning "$release not found, skipping..."
    fi
  done

  # Wait for all uninstalls to complete
  wait

  print_success "All Helm releases uninstalled"
}

# Delete Dapr components
delete_dapr_components() {
  print_step "Deleting Dapr components..."

  local dapr_dir=""
  if [ "$ENVIRONMENT" = "local" ]; then
    dapr_dir="specs/005-event-driven-microservices/contracts/dapr-components/local"
  else
    dapr_dir="specs/005-event-driven-microservices/contracts/dapr-components/cloud"
  fi

  if [ -d "$dapr_dir" ]; then
    kubectl delete -f $dapr_dir/ --ignore-not-found=true
    print_success "Dapr components deleted"
  else
    print_warning "Dapr components directory not found, skipping..."
  fi
}

# Delete Kubernetes secrets
delete_secrets() {
  if [ "$KEEP_SECRETS" = true ]; then
    print_warning "Keeping Kubernetes secrets (--keep-secrets flag)"
    return
  fi

  print_step "Deleting Kubernetes secrets..."

  local secrets=(
    "postgres-credentials"
    "openai-credentials"
    "better-auth-secret"
    "redpanda-credentials"
  )

  for secret in "${secrets[@]}"; do
    if kubectl get secret $secret &> /dev/null; then
      kubectl delete secret $secret
      print_success "Deleted secret: $secret"
    fi
  done

  print_success "All secrets deleted"
}

# Stop Redpanda Docker container
stop_redpanda() {
  if [ "$ENVIRONMENT" != "local" ]; then
    return
  fi

  print_step "Stopping Redpanda Docker container..."

  if docker ps -a --format '{{.Names}}' | grep -q "^redpanda$"; then
    docker stop redpanda &> /dev/null || true
    docker rm redpanda &> /dev/null || true
    print_success "Redpanda container stopped and removed"
  else
    print_warning "Redpanda container not found, skipping..."
  fi
}

# Stop Minikube
stop_minikube() {
  if [ "$ENVIRONMENT" != "local" ]; then
    return
  fi

  print_step "Checking Minikube status..."

  if ! command -v minikube &> /dev/null; then
    print_warning "Minikube not installed, skipping..."
    return
  fi

  if minikube status &> /dev/null; then
    print_step "Stopping Minikube..."

    read -p "Do you want to delete the Minikube cluster? (yes/no): " -r
    echo ""

    if [[ $REPLY =~ ^[Yy](es)?$ ]]; then
      minikube delete
      print_success "Minikube cluster deleted"
    else
      minikube stop
      print_success "Minikube cluster stopped (can be restarted with 'minikube start')"
    fi
  else
    print_warning "Minikube is not running, skipping..."
  fi
}

# Verify cleanup
verify_cleanup() {
  print_step "Verifying cleanup..."

  # Check Helm releases
  if helm list | grep -q -E "(backend-api|frontend|notification-service|recurring-task-service|audit-service|websocket-service)"; then
    print_warning "Some Helm releases may still exist"
  else
    print_success "All Helm releases removed"
  fi

  # Check pods
  local pod_count=$(kubectl get pods --no-headers 2>/dev/null | wc -l)
  if [ $pod_count -gt 0 ]; then
    print_warning "Some pods may still exist (terminating...)"
    kubectl get pods
  else
    print_success "All pods removed"
  fi

  # Check Dapr components
  local dapr_count=$(kubectl get components.dapr.io --no-headers 2>/dev/null | wc -l)
  if [ $dapr_count -gt 0 ]; then
    print_warning "Some Dapr components may still exist"
  else
    print_success "All Dapr components removed"
  fi

  # Check Redpanda (local only)
  if [ "$ENVIRONMENT" = "local" ]; then
    if docker ps --format '{{.Names}}' | grep -q "^redpanda$"; then
      print_warning "Redpanda container is still running"
    else
      print_success "Redpanda container removed"
    fi
  fi
}

# Show final status
show_final_status() {
  echo ""
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}Teardown Complete!${NC}"
  echo -e "${GREEN}========================================${NC}"
  echo ""
  echo "Environment: $ENVIRONMENT"
  echo ""

  if [ "$ENVIRONMENT" = "local" ]; then
    echo "Local resources cleaned up:"
    echo "  ✓ Helm releases uninstalled"
    echo "  ✓ Dapr components removed"
    echo "  ✓ Redpanda container stopped"

    if [ "$KEEP_SECRETS" = false ]; then
      echo "  ✓ Kubernetes secrets deleted"
    else
      echo "  - Kubernetes secrets kept"
    fi

    echo ""
    echo "To redeploy:"
    echo "  ./infrastructure/scripts/deploy-local.sh"
  else
    echo "Cloud resources cleaned up:"
    echo "  ✓ Helm releases uninstalled"
    echo "  ✓ Dapr components removed"

    if [ "$KEEP_SECRETS" = false ]; then
      echo "  ✓ Kubernetes secrets deleted"
    else
      echo "  - Kubernetes secrets kept"
    fi

    echo ""
    echo "Note: Kubernetes cluster is still running"
    echo ""
    echo "To redeploy:"
    echo "  ./infrastructure/scripts/deploy-cloud.sh"
  fi

  echo ""
}

# Main execution
main() {
  echo ""
  echo -e "${YELLOW}========================================${NC}"
  echo -e "${YELLOW}Evolution of Todo - Phase V${NC}"
  echo -e "${YELLOW}Teardown Script${NC}"
  echo -e "${YELLOW}========================================${NC}"
  echo ""

  detect_environment
  confirm_teardown

  uninstall_helm_releases
  delete_dapr_components
  delete_secrets
  stop_redpanda
  stop_minikube

  verify_cleanup
  show_final_status
}

# Run main function
main
