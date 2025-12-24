#!/bin/bash

# Create deployment package for Oracle Cloud
# Usage: ./scripts/create-deployment-package.sh

set -e

echo "📦 Creating deployment package for Todo AI..."

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Create package name with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="todo-ai-${TIMESTAMP}.tar.gz"

echo "🔨 Building frontend..."
cd frontend
npm run build
cd ..

echo "📋 Generating backend requirements.txt..."
cd backend
if command -v uv &> /dev/null; then
    uv pip compile pyproject.toml -o requirements.txt
else
    echo "⚠️  'uv' not found, skipping requirements.txt generation"
    echo "   Please create requirements.txt manually or install uv"
fi
cd ..

echo "📦 Creating tarball..."
tar -czf "$PACKAGE_NAME" \
    --exclude='node_modules' \
    --exclude='.next/cache' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='.env.production' \
    frontend/ \
    backend/ \
    DEPLOYMENT.md \
    README.md

echo "✅ Deployment package created: $PACKAGE_NAME"
echo ""
echo "📤 To upload to Oracle Cloud:"
echo "   scp $PACKAGE_NAME ubuntu@<your-instance-ip>:~"
echo ""
echo "📝 Don't forget to:"
echo "   1. Set up environment variables on the server"
echo "   2. Update NEXT_PUBLIC_API_URL in frontend"
echo "   3. Update BETTER_AUTH_ISSUER and JWKS_URL in backend"
echo "   4. Generate a production BETTER_AUTH_SECRET"
