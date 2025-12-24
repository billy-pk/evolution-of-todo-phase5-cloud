# Quick Deployment Guide - Oracle Cloud

## TL;DR - Deployment Steps

### 1️⃣ **Prepare Locally**

```bash
# Generate production secret
openssl rand -base64 32

# Save this secret - you'll need it for both frontend and backend!

# Create deployment package
bash scripts/create-deployment-package.sh
```

### 2️⃣ **Set Up Oracle Cloud Instance**

1. Create Ubuntu 22.04 LTS VM
2. Add SSH key
3. Configure Security Lists (ports 22, 80, 443)
4. Note the public IP address

### 3️⃣ **Upload to Server**

```bash
# Upload package
scp todo-ai-*.tar.gz ubuntu@<your-ip>:~

# Upload server setup script
scp scripts/server-setup.sh ubuntu@<your-ip>:~
```

### 4️⃣ **Initial Server Setup**

```bash
# SSH into server
ssh ubuntu@<your-ip>

# Run setup script
bash server-setup.sh

# Extract application
tar -xzf todo-ai-*.tar.gz -C /var/www/todo-ai
cd /var/www/todo-ai
```

### 5️⃣ **Configure Environment Variables**

**Frontend** (`/var/www/todo-ai/frontend/.env.production`):
```env
NEXT_PUBLIC_API_URL=http://<your-ip>
BETTER_AUTH_SECRET=<your-generated-secret>
BETTER_AUTH_URL=http://<your-ip>
DATABASE_URL=<your-neon-postgres-url>
```

**Backend** (`/var/www/todo-ai/backend/.env`):
```env
DATABASE_URL=<your-neon-postgres-url>
BETTER_AUTH_SECRET=<same-secret-as-frontend>
BETTER_AUTH_ISSUER=http://<your-ip>
BETTER_AUTH_JWKS_URL=http://<your-ip>/api/auth/jwks
OPENAI_API_KEY=<your-openai-key>
MCP_SERVER_URL=http://localhost:8001
```

⚠️ **Critical**: `BETTER_AUTH_SECRET` MUST be the same in both files!

### 6️⃣ **Deploy Application**

```bash
cd /var/www/todo-ai
bash scripts/deploy-app.sh
```

### 7️⃣ **Configure Nginx**

```bash
sudo nano /etc/nginx/sites-available/todo-ai
```

Paste the Nginx config from `DEPLOYMENT.md` (Part 6).

Then:
```bash
sudo ln -s /etc/nginx/sites-available/todo-ai /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 8️⃣ **Test Your App**

Visit: `http://<your-ip>`

✅ You should see the landing page!

---

## 🌐 Add Domain & SSL (Optional but Recommended)

### Point Domain to IP

1. Go to your domain registrar
2. Add A record: `@ → <your-ip>`
3. Add A record: `www → <your-ip>`

### Install SSL Certificate

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Select option to redirect HTTP to HTTPS
```

### Update Environment Variables

Update URLs from `http://` to `https://` and from IP to domain:

**Frontend** `.env.production`:
```env
NEXT_PUBLIC_API_URL=https://yourdomain.com
BETTER_AUTH_URL=https://yourdomain.com
```

**Backend** `.env`:
```env
BETTER_AUTH_ISSUER=https://yourdomain.com
BETTER_AUTH_JWKS_URL=https://yourdomain.com/api/auth/jwks
```

Restart:
```bash
pm2 restart all
```

---

## 📊 Monitoring Commands

```bash
# Check status
pm2 status

# View logs
pm2 logs

# Monitor resources
pm2 monit

# Restart service
pm2 restart todo-frontend
pm2 restart todo-backend
pm2 restart todo-mcp

# Restart all
pm2 restart all
```

---

## 🔧 Troubleshooting

### Frontend not loading
```bash
pm2 logs todo-frontend
# Check if build was successful
cd /var/www/todo-ai/frontend
npm run build
```

### Backend API error
```bash
pm2 logs todo-backend
# Check environment variables
cat /var/www/todo-ai/backend/.env
```

### Database connection error
- Verify `DATABASE_URL` is correct
- Check if Neon database is accessible
- Test connection: `psql <DATABASE_URL>`

### MCP server not responding
```bash
pm2 logs todo-mcp
# Restart MCP server
pm2 restart todo-mcp
```

---

## 🔄 Update Deployment

When you make changes:

```bash
# On local machine
bash scripts/create-deployment-package.sh
scp todo-ai-*.tar.gz ubuntu@<your-ip>:~

# On server
ssh ubuntu@<your-ip>
cd /var/www/todo-ai
tar -xzf ~/todo-ai-*.tar.gz
bash scripts/deploy-app.sh
```

---

## 💰 Oracle Cloud Free Tier

Your app should fit within Oracle's **Always Free** tier:
- ✅ 2 AMD Compute VMs
- ✅ 200 GB Storage
- ✅ 10 TB bandwidth/month

Perfect for this application! 🎉

---

## 🆘 Need Help?

See the full guide: `DEPLOYMENT.md`

Common issues:
- **Port conflicts**: Check if ports 3000, 8000, 8001 are free
- **Permission errors**: Ensure `/var/www/todo-ai` is owned by your user
- **Secret mismatch**: Frontend and backend must use same `BETTER_AUTH_SECRET`
- **Database errors**: Check Neon PostgreSQL connection string
