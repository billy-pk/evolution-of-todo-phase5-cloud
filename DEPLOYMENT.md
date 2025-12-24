# Oracle Cloud Deployment Guide - Todo AI

This guide covers deploying the Todo AI application (Next.js + FastAPI + MCP) to Oracle Cloud.

## Architecture Overview

Your application consists of:
- **Frontend**: Next.js 16 (App Router)
- **Backend API**: FastAPI (Python 3.13)
- **MCP Server**: FastMCP (Task management tools)
- **Database**: Neon PostgreSQL (already cloud-hosted)
- **Auth**: Better Auth with JWT

## Deployment Options on Oracle Cloud

### Option 1: Single VM Instance (Recommended for Simplicity)
Deploy all components on one Oracle Cloud Compute instance.

**Pros:**
- Simple setup
- Lower cost
- Easy to manage

**Cons:**
- Single point of failure
- Limited scalability

### Option 2: Separate VM Instances
Deploy frontend, backend, and MCP server on separate instances.

**Pros:**
- Better isolation
- Independent scaling
- More resilient

**Cons:**
- Higher cost
- More complex networking

### Option 3: Container-based (OCI Container Instances)
Use Docker containers for each service.

**Pros:**
- Portable
- Easy updates
- Better resource utilization

**Cons:**
- Requires Docker knowledge
- Initial setup complexity

---

## Prerequisites

1. **Oracle Cloud Account** with active tenancy
2. **Oracle Cloud Compute Instance** (Ubuntu 22.04 LTS recommended)
   - Shape: VM.Standard.E2.1.Micro (Always Free tier) or higher
   - Minimum: 1 OCPU, 1GB RAM
   - Recommended: 2 OCPU, 8GB RAM
3. **Domain name** (optional, but recommended)
4. **SSL certificate** (Let's Encrypt recommended)

---

## Part 1: Frontend Build & Preparation

### Step 1: Build the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Test production build locally
npm start
```

The build output will be in `frontend/.next` directory.

### Step 2: Update Frontend Environment Variables

Create `frontend/.env.production`:

```env
# Backend API URL (will be your Oracle Cloud IP or domain)
NEXT_PUBLIC_API_URL=https://your-domain.com/api

# Better Auth Configuration
BETTER_AUTH_SECRET=your-production-secret-here
BETTER_AUTH_URL=https://your-domain.com

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require
```

**Important:** Generate a strong `BETTER_AUTH_SECRET`:
```bash
openssl rand -base64 32
```

---

## Part 2: Backend Preparation

### Step 1: Export Backend Dependencies

```bash
cd backend

# Create requirements.txt from pyproject.toml
uv pip compile pyproject.toml -o requirements.txt
```

Or manually create `requirements.txt`:

```txt
fastapi>=0.124.0
uvicorn[standard]>=0.38.0
sqlmodel>=0.0.27
pydantic>=2.12.5
pydantic-settings>=2.12.0
pyjwt[crypto]>=2.10.1
python-jose[cryptography]>=3.5.0
psycopg2-binary>=2.9.11
python-multipart>=0.0.20
mcp>=1.24.0
openai-agents>=0.6.3
openai-chatkit>=1.4.0
cryptography>=46.0.3
httpx>=0.28.1
```

### Step 2: Update Backend Environment Variables

Create `backend/.env.production`:

```env
# Database
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require

# Better Auth (MUST match frontend secret)
BETTER_AUTH_SECRET=your-production-secret-here
BETTER_AUTH_ISSUER=https://your-domain.com
BETTER_AUTH_JWKS_URL=https://your-domain.com/api/auth/jwks

# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# MCP Server
MCP_SERVER_URL=http://localhost:8001
```

---

## Part 3: Oracle Cloud Setup

### Step 1: Create Compute Instance

1. Go to **Oracle Cloud Console** → **Compute** → **Instances**
2. Click **Create Instance**
3. Choose:
   - **Name**: todo-ai-server
   - **Image**: Ubuntu 22.04 LTS
   - **Shape**: VM.Standard.E2.1.Micro (or higher)
   - **Network**: Create new VCN or use existing
   - **Public IP**: Assign a public IP
4. **Add SSH Key**: Upload your public SSH key
5. Click **Create**

### Step 2: Configure Firewall Rules

1. Go to **Networking** → **Virtual Cloud Networks**
2. Select your VCN → **Security Lists**
3. Add **Ingress Rules**:

```
Port 22   - SSH (0.0.0.0/0)
Port 80   - HTTP (0.0.0.0/0)
Port 443  - HTTPS (0.0.0.0/0)
Port 3000 - Next.js (optional, for testing)
Port 8000 - FastAPI (optional, for testing)
```

### Step 3: Configure Ubuntu Firewall

SSH into your instance:

```bash
ssh ubuntu@<your-instance-public-ip>
```

Configure firewall:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Part 4: Install Dependencies on Oracle Cloud

### Step 1: Install Node.js

```bash
# Install Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version  # Should be v20.x
npm --version
```

### Step 2: Install Python 3.13

```bash
# Add deadsnakes PPA for Python 3.13
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.13
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# Install pip
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.13

# Verify
python3.13 --version
```

### Step 3: Install Nginx (Reverse Proxy)

```bash
sudo apt install -y nginx

# Start and enable
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 4: Install PM2 (Process Manager)

```bash
# Install PM2 globally
sudo npm install -g pm2

# Verify
pm2 --version
```

---

## Part 5: Deploy Application

### Step 1: Upload Code to Server

From your local machine:

```bash
# Create deployment package (from project root)
tar -czf todo-ai.tar.gz \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='__pycache__' \
  --exclude='.venv' \
  frontend/ backend/ DEPLOYMENT.md

# Upload to Oracle Cloud
scp todo-ai.tar.gz ubuntu@<your-instance-ip>:~
```

### Step 2: Extract and Setup on Server

SSH into server:

```bash
ssh ubuntu@<your-instance-ip>

# Create app directory
sudo mkdir -p /var/www/todo-ai
sudo chown ubuntu:ubuntu /var/www/todo-ai

# Extract
tar -xzf todo-ai.tar.gz -C /var/www/todo-ai
cd /var/www/todo-ai
```

### Step 3: Setup Frontend

```bash
cd /var/www/todo-ai/frontend

# Install dependencies
npm install --production

# Build
npm run build

# Start with PM2
pm2 start npm --name "todo-frontend" -- start

# Save PM2 configuration
pm2 save
pm2 startup
```

### Step 4: Setup Backend API

```bash
cd /var/www/todo-ai/backend

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start with PM2
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name "todo-backend"
```

### Step 5: Setup MCP Server

```bash
cd /var/www/todo-ai/backend/tools

# Use same virtual environment
source ../venv/bin/activate

# Start with PM2
pm2 start "python server.py" --name "todo-mcp"

# Save all PM2 processes
pm2 save
```

### Step 6: Verify Services

```bash
# Check PM2 status
pm2 status

# Should show:
# todo-frontend - online
# todo-backend  - online
# todo-mcp      - online

# Check logs
pm2 logs todo-frontend --lines 50
pm2 logs todo-backend --lines 50
pm2 logs todo-mcp --lines 50
```

---

## Part 6: Configure Nginx Reverse Proxy

### Step 1: Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/todo-ai
```

Add this configuration:

```nginx
# Frontend (Next.js)
upstream frontend {
    server 127.0.0.1:3000;
}

# Backend API (FastAPI)
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to Next.js frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy to FastAPI backend
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers (if needed)
        add_header Access-Control-Allow-Origin * always;
    }

    # ChatKit endpoint
    location /chatkit {
        proxy_pass http://backend/chatkit;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Next.js static files
    location /_next/static {
        proxy_pass http://frontend/_next/static;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
}
```

### Step 2: Enable Configuration

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/todo-ai /etc/nginx/sites-enabled/

# Remove default
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## Part 7: SSL Certificate (HTTPS)

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow prompts and select redirect HTTP to HTTPS

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## Part 8: Environment Variables

### Update Production URLs

After deployment, update environment variables:

**Frontend** (`/var/www/todo-ai/frontend/.env.production`):
```env
NEXT_PUBLIC_API_URL=https://your-domain.com
BETTER_AUTH_URL=https://your-domain.com
```

**Backend** (`/var/www/todo-ai/backend/.env`):
```env
BETTER_AUTH_ISSUER=https://your-domain.com
BETTER_AUTH_JWKS_URL=https://your-domain.com/api/auth/jwks
```

Restart services:
```bash
pm2 restart all
```

---

## Part 9: Monitoring & Maintenance

### Monitor Services

```bash
# PM2 monitoring
pm2 monit

# View logs
pm2 logs

# Check Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Auto-restart on Reboot

```bash
# PM2 startup script (already done)
pm2 startup
pm2 save
```

### Update Application

```bash
# On local machine - create new package
tar -czf todo-ai-update.tar.gz frontend/ backend/

# Upload
scp todo-ai-update.tar.gz ubuntu@<ip>:~

# On server
cd /var/www/todo-ai
tar -xzf ~/todo-ai-update.tar.gz

# Rebuild frontend
cd frontend
npm install
npm run build

# Restart services
pm2 restart all
```

---

## Part 10: Verify Deployment

### Test Checklist

- [ ] Visit `https://your-domain.com` - Landing page loads
- [ ] Sign up for new account - Works without errors
- [ ] Sign in - Redirects to `/chat`
- [ ] Chat interface loads - ChatKit UI appears
- [ ] Input box visible - Can type messages
- [ ] Send message to AI - Gets response
- [ ] Create task via chat - Task appears in database
- [ ] Logout works - Redirects to signin

### Health Check URLs

```bash
# Backend API
curl https://your-domain.com/api/docs

# Frontend
curl https://your-domain.com
```

---

## Troubleshooting

### Frontend not loading
```bash
pm2 logs todo-frontend
# Check port 3000 is not already in use
sudo netstat -tulpn | grep 3000
```

### Backend API errors
```bash
pm2 logs todo-backend
# Check database connection
# Verify environment variables
```

### MCP server not responding
```bash
pm2 logs todo-mcp
# Verify port 8001 is accessible
```

### Nginx errors
```bash
sudo nginx -t
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

---

## Security Best Practices

1. **Firewall**: Only expose ports 22, 80, 443
2. **SSH**: Use key-based authentication, disable password login
3. **Secrets**: Never commit `.env` files to git
4. **Updates**: Regularly update system packages
5. **Backups**: Backup database regularly (Neon provides automated backups)
6. **Monitoring**: Set up uptime monitoring (UptimeRobot, etc.)

---

## Cost Optimization

Oracle Cloud Free Tier includes:
- 2 AMD-based Compute VMs (Always Free)
- 200 GB Block Volume Storage (Always Free)
- 10 TB outbound data transfer per month (Always Free)

This is sufficient for your Todo AI application!

---

## Summary

**Yes, you should run `npm run build`** before deployment, but that's just one step. The complete deployment process involves:

1. ✅ Build frontend (`npm run build`)
2. ✅ Prepare backend dependencies
3. ✅ Set up Oracle Cloud instance
4. ✅ Install Node.js, Python, Nginx
5. ✅ Deploy code to server
6. ✅ Configure reverse proxy
7. ✅ Set up SSL certificate
8. ✅ Configure environment variables
9. ✅ Start services with PM2
10. ✅ Test and monitor

Your app will be accessible at `https://your-domain.com`!
