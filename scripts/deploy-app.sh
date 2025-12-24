#!/bin/bash

# Deploy Todo AI application on Oracle Cloud server
# This script should be run from /var/www/todo-ai directory
# Usage: bash scripts/deploy-app.sh

set -e

echo "🚀 Deploying Todo AI application..."
echo ""

# Check if we're in the right directory
if [ ! -d "frontend" ] || [ ! -d "backend" ]; then
    echo "❌ Error: Must run from /var/www/todo-ai directory"
    echo "   Current directory: $(pwd)"
    exit 1
fi

# Check for environment files
if [ ! -f "frontend/.env.production" ]; then
    echo "⚠️  Warning: frontend/.env.production not found"
    echo "   Please create it before continuing"
    exit 1
fi

if [ ! -f "backend/.env" ]; then
    echo "⚠️  Warning: backend/.env not found"
    echo "   Please create it before continuing"
    exit 1
fi

# Deploy Frontend
echo "📦 Deploying Frontend..."
cd frontend
npm install --production
npm run build

# Stop existing frontend if running
pm2 delete todo-frontend 2>/dev/null || true

# Start frontend with PM2
pm2 start npm --name "todo-frontend" -- start
cd ..

# Deploy Backend
echo "🐍 Deploying Backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    python3.13 -m venv venv
fi

source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Stop existing backend if running
pm2 delete todo-backend 2>/dev/null || true

# Start backend with PM2
pm2 start "$(pwd)/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000" --name "todo-backend"
cd ..

# Deploy MCP Server
echo "🔧 Deploying MCP Server..."
cd backend/tools

# Use same virtual environment
source ../venv/bin/activate

# Stop existing MCP server if running
pm2 delete todo-mcp 2>/dev/null || true

# Start MCP server with PM2
pm2 start "$(pwd)/../venv/bin/python server.py" --name "todo-mcp"
cd ../..

# Save PM2 configuration
echo "💾 Saving PM2 configuration..."
pm2 save

# Setup PM2 startup script
pm2 startup | grep "sudo" | sh || true

# Show status
echo ""
echo "📊 Application Status:"
pm2 status

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Configure Nginx reverse proxy"
echo "   2. Set up SSL certificate with Certbot"
echo "   3. Test the application"
echo ""
echo "📋 Useful commands:"
echo "   pm2 status          - Check application status"
echo "   pm2 logs            - View logs"
echo "   pm2 restart all     - Restart all services"
echo "   pm2 monit           - Monitor resources"
