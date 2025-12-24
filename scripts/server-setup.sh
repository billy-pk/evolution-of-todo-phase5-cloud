#!/bin/bash

# Server setup script for Oracle Cloud Ubuntu instance
# Run this on your Oracle Cloud server after uploading the deployment package
# Usage: bash server-setup.sh

set -e

echo "🚀 Setting up Todo AI on Oracle Cloud..."
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run as root. Run as ubuntu user."
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Node.js 20.x
echo "📦 Installing Node.js 20.x..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi
node --version
npm --version

# Install Python 3.13
echo "🐍 Installing Python 3.13..."
if ! command -v python3.13 &> /dev/null; then
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.13 python3.13-venv python3.13-dev
    curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.13
fi
python3.13 --version

# Install Nginx
echo "🌐 Installing Nginx..."
if ! command -v nginx &> /dev/null; then
    sudo apt install -y nginx
    sudo systemctl start nginx
    sudo systemctl enable nginx
fi

# Install PM2
echo "⚙️  Installing PM2..."
if ! command -v pm2 &> /dev/null; then
    sudo npm install -g pm2
fi
pm2 --version

# Configure firewall
echo "🔒 Configuring firewall..."
sudo ufw --force enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status

# Create app directory
echo "📁 Creating application directory..."
sudo mkdir -p /var/www/todo-ai
sudo chown $USER:$USER /var/www/todo-ai

echo ""
echo "✅ Server setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Extract your deployment package to /var/www/todo-ai"
echo "   2. Set up environment variables (.env files)"
echo "   3. Run the deployment script"
echo ""
echo "Example:"
echo "   tar -xzf todo-ai-*.tar.gz -C /var/www/todo-ai"
echo "   cd /var/www/todo-ai"
echo "   bash scripts/deploy-app.sh"
