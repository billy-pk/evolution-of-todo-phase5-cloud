# Cloud Deployment Guide - Oracle Cloud Always Free Tier

Deploy to Oracle Cloud Infrastructure using Always Free resources with Neon DB.

## Overview

**Target Setup:**
- Oracle Compute VM (Always Free: 1GB RAM Micro instance)
- K3s (lightweight Kubernetes)
- Neon PostgreSQL (external, free tier)
- Traefik Ingress (included with K3s)
- Let's Encrypt SSL (free)

**Total Cost: $0/month**

---

## Prerequisites

- Oracle Cloud account (Always Free tier)
- Neon DB account with database created
- Domain name (optional, can use nip.io for testing)
- Local machine with Docker and kubectl

---

## Step 1: Create Oracle Compute Instance

### 1.1 Via OCI Console

```
1. Login to cloud.oracle.com
2. Navigate: Compute → Instances → Create Instance
3. Configure:
   - Name: ai-todo-k8s
   - Image: Ubuntu 22.04 (Always Free eligible)
   - Shape: VM.Standard.E2.1.Micro (Always Free: 1GB RAM, 1 OCPU)
   - Network: Create new VCN or use existing
   - Public IP: Assign public IPv4 address
   - SSH Keys: Upload your public key (~/.ssh/id_rsa.pub)
4. Click "Create"
5. Note the public IP address
```

### 1.2 Configure Firewall (Security List)

```
Navigate: Networking → Virtual Cloud Networks → Your VCN → Security Lists

Add Ingress Rules:
- Source: 0.0.0.0/0, Protocol: TCP, Destination Port: 22 (SSH)
- Source: 0.0.0.0/0, Protocol: TCP, Destination Port: 80 (HTTP)
- Source: 0.0.0.0/0, Protocol: TCP, Destination Port: 443 (HTTPS)
- Source: 0.0.0.0/0, Protocol: TCP, Destination Port: 6443 (K8s API - optional)
```

---

## Step 2: Install K3s on Compute Instance

### 2.1 Connect and Install

```bash
# SSH into instance
ssh ubuntu@<instance-public-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install K3s (lightweight Kubernetes, perfect for 1GB RAM)
curl -sfL https://get.k3s.io | sh -

# Verify installation
sudo k3s kubectl get nodes

# Expected output:
# NAME              STATUS   ROLES                  AGE   VERSION
# ai-todo-k8s       Ready    control-plane,master   1m    v1.28.x
```

### 2.2 Configure kubectl Access from Local Machine

```bash
# On compute instance - copy kubeconfig
sudo cat /etc/rancher/k3s/k3s.yaml

# On local machine - create config file
nano ~/k3s-oracle.yaml

# Paste content and edit:
# Replace: server: https://127.0.0.1:6443
# With:    server: https://<instance-public-ip>:6443

# Set KUBECONFIG
export KUBECONFIG=~/k3s-oracle.yaml

# Test connection
kubectl get nodes
```

### 2.3 Configure Instance Firewall (iptables)

```bash
# On compute instance
# Oracle Linux has built-in firewall that blocks K8s ports

# Allow HTTP/HTTPS through iptables
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 6443 -j ACCEPT

# Save rules
sudo netfilter-persistent save

# Or install netfilter-persistent if not present
sudo apt install -y iptables-persistent
sudo netfilter-persistent save
```

---

## Step 3: Build and Transfer Docker Images

### 3.1 Build Images Locally

```bash
# On local machine
cd /path/to/evolution-of-todo/phase4-k8s

# Build all images
./deployment/build-images.sh

# Verify images
docker images | grep ai-todo
```

### 3.2 Save and Transfer Images

```bash
# Save images as tar files
docker save ai-todo-backend:latest | gzip > ai-todo-backend.tar.gz
docker save ai-todo-frontend:latest | gzip > ai-todo-frontend.tar.gz
docker save ai-todo-mcp:latest | gzip > ai-todo-mcp.tar.gz

# Transfer to compute instance
scp ai-todo-*.tar.gz ubuntu@<instance-ip>:/home/ubuntu/

# On compute instance - load images into K3s
ssh ubuntu@<instance-ip>

sudo k3s ctr images import ai-todo-backend.tar.gz
sudo k3s ctr images import ai-todo-frontend.tar.gz
sudo k3s ctr images import ai-todo-mcp.tar.gz

# Verify
sudo k3s crictl images | grep ai-todo

# Cleanup
rm ai-todo-*.tar.gz
```

---

## Step 4: Install Helm on Compute Instance

```bash
# On compute instance
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify
helm version

# Configure to use K3s kubeconfig
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

---

## Step 5: Create Kubernetes Secrets

### 5.1 Create Secrets

```bash
# On compute instance
sudo k3s kubectl create secret generic ai-todo-backend-secrets \
  --from-literal=DATABASE_URL='postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require' \
  --from-literal=OPENAI_API_KEY='sk-proj-...' \
  --from-literal=BETTER_AUTH_SECRET='your-base64-secret-key'

sudo k3s kubectl create secret generic ai-todo-frontend-secrets \
  --from-literal=DATABASE_URL='postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require' \
  --from-literal=BETTER_AUTH_SECRET='your-base64-secret-key'

sudo k3s kubectl create secret generic ai-todo-mcp-secrets \
  --from-literal=DATABASE_URL='postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require'

# Verify
sudo k3s kubectl get secrets
```

### 5.2 Create ConfigMaps

```bash
# Get instance public IP
INSTANCE_IP=$(curl -s ifconfig.me)

# Backend ConfigMap
sudo k3s kubectl create configmap ai-todo-backend-config \
  --from-literal=BETTER_AUTH_URL="http://ai-todo-frontend-service:3000" \
  --from-literal=BETTER_AUTH_ISSUER="http://$INSTANCE_IP" \
  --from-literal=BETTER_AUTH_JWKS_URL="http://ai-todo-frontend-service:3000/api/auth/jwks" \
  --from-literal=MCP_SERVER_URL="http://ai-todo-mcp-service:8001"

# Frontend ConfigMap
sudo k3s kubectl create configmap ai-todo-frontend-config \
  --from-literal=NEXT_PUBLIC_API_URL="http://$INSTANCE_IP:8000" \
  --from-literal=BETTER_AUTH_URL="http://$INSTANCE_IP:3000"

# Verify
sudo k3s kubectl get configmap
```

---

## Step 6: Update Helm Charts for K3s

### 6.1 Update Image Pull Policy

```bash
# On local machine or compute instance
# Edit charts/*/values.yaml

# Backend
image:
  repository: ai-todo-backend
  tag: latest
  pullPolicy: Never  # Images loaded locally, don't pull

service:
  type: ClusterIP  # Will expose via Ingress
  port: 8000

# Repeat for frontend and MCP charts
```

### 6.2 Transfer Helm Charts

```bash
# On local machine
cd /path/to/evolution-of-todo/phase4-k8s
tar czf charts.tar.gz charts/

scp charts.tar.gz ubuntu@<instance-ip>:/home/ubuntu/

# On compute instance
tar xzf charts.tar.gz
```

---

## Step 7: Deploy with Helm

```bash
# On compute instance
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Deploy MCP server
sudo helm install ai-todo-mcp ./charts/ai-todo-mcp

# Deploy backend
sudo helm install ai-todo-backend ./charts/ai-todo-backend

# Deploy frontend
sudo helm install ai-todo-frontend ./charts/ai-todo-frontend

# Check deployment
sudo k3s kubectl get pods
sudo k3s kubectl get svc

# Wait for all pods to be ready
watch sudo k3s kubectl get pods
```

---

## Step 8: Setup Ingress (Traefik)

K3s comes with Traefik ingress controller by default.

### 8.1 Create Ingress Resource

```bash
# On compute instance
INSTANCE_IP=$(curl -s ifconfig.me)

sudo k3s kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-todo-ingress
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web
spec:
  rules:
  - host: $INSTANCE_IP.nip.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-todo-frontend-service
            port:
              number: 3000
  - host: api.$INSTANCE_IP.nip.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-todo-backend-service
            port:
              number: 8000
EOF
```

### 8.2 Access Application

```bash
# Get public IP
INSTANCE_IP=$(curl -s ifconfig.me)

echo "Frontend: http://$INSTANCE_IP.nip.io"
echo "Backend:  http://api.$INSTANCE_IP.nip.io"

# Test
curl http://$INSTANCE_IP.nip.io
curl http://api.$INSTANCE_IP.nip.io/health
```

**Note:** nip.io is a free DNS service that maps `<ip>.nip.io` to `<ip>`.

---

## Step 9: Setup Custom Domain (Optional)

### 9.1 Configure DNS

```bash
# Add A records in your domain registrar:
# app.yourdomain.com → <instance-ip>
# api.yourdomain.com → <instance-ip>
```

### 9.2 Update Ingress

```bash
sudo k3s kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-todo-ingress
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web,websecure
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - app.yourdomain.com
    - api.yourdomain.com
    secretName: ai-todo-tls
  rules:
  - host: app.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-todo-frontend-service
            port:
              number: 3000
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-todo-backend-service
            port:
              number: 8000
EOF
```

### 9.3 Setup Let's Encrypt SSL

```bash
# Install cert-manager
sudo k3s kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml

# Wait for cert-manager pods
sudo k3s kubectl get pods -n cert-manager -w

# Create ClusterIssuer
sudo k3s kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: traefik
EOF

# Verify certificate
sudo k3s kubectl get certificate
sudo k3s kubectl describe certificate ai-todo-tls
```

---

## Step 10: Update Environment for Production

### 10.1 Update Frontend ConfigMap

```bash
sudo k3s kubectl delete configmap ai-todo-frontend-config

sudo k3s kubectl create configmap ai-todo-frontend-config \
  --from-literal=NEXT_PUBLIC_API_URL='https://api.yourdomain.com' \
  --from-literal=BETTER_AUTH_URL='https://app.yourdomain.com'

sudo k3s kubectl rollout restart deployment/ai-todo-frontend
```

### 10.2 Update Backend ConfigMap

```bash
sudo k3s kubectl delete configmap ai-todo-backend-config

sudo k3s kubectl create configmap ai-todo-backend-config \
  --from-literal=BETTER_AUTH_URL='http://ai-todo-frontend-service:3000' \
  --from-literal=BETTER_AUTH_ISSUER='https://app.yourdomain.com' \
  --from-literal=BETTER_AUTH_JWKS_URL='http://ai-todo-frontend-service:3000/api/auth/jwks' \
  --from-literal=MCP_SERVER_URL='http://ai-todo-mcp-service:8001'

sudo k3s kubectl rollout restart deployment/ai-todo-backend
```

---

## Updating Code

### From Local Machine

```bash
# 1. Rebuild images locally
./deployment/build-images.sh

# 2. Save and transfer
docker save ai-todo-backend:latest | gzip > ai-todo-backend.tar.gz
scp ai-todo-backend.tar.gz ubuntu@<instance-ip>:/home/ubuntu/

# 3. Load on instance
ssh ubuntu@<instance-ip>
sudo k3s ctr images import ai-todo-backend.tar.gz
sudo k3s crictl rmi ai-todo-backend:latest  # Force reload
sudo k3s kubectl delete pod -l app=ai-todo-backend

# 4. Cleanup
rm ai-todo-backend.tar.gz
```

### Build on Instance (Alternative)

```bash
# 1. Transfer code
rsync -avz --exclude node_modules --exclude .venv \
  ../evolution-of-todo ubuntu@<instance-ip>:/home/ubuntu/

# 2. Build on instance
ssh ubuntu@<instance-ip>
cd evolution-of-todo/phase4-k8s
sudo docker build -t ai-todo-backend:latest -f dockerfiles/backend.Dockerfile backend/

# 3. Restart pods
sudo k3s kubectl delete pod -l app=ai-todo-backend
```

---

## Monitoring & Maintenance

### Check Resource Usage

```bash
# On compute instance
free -h  # Memory usage
df -h    # Disk usage
top      # CPU/process usage

# K8s resource usage
sudo k3s kubectl top nodes
sudo k3s kubectl top pods
```

### View Logs

```bash
sudo k3s kubectl logs -l app=ai-todo-backend --tail=100
sudo k3s kubectl logs -l app=ai-todo-frontend --tail=100
sudo k3s kubectl logs -l app=ai-todo-mcp --tail=100
```

### Backup Database

```bash
# Neon DB has automatic backups
# Access via Neon dashboard: https://console.neon.tech
```

### Update System

```bash
# Monthly updates recommended
sudo apt update && sudo apt upgrade -y
sudo reboot
```

---

## Troubleshooting

### Pods Not Starting (OutOfMemory)

```bash
# Check memory
free -h

# Reduce resource requests in values.yaml
resources:
  requests:
    memory: 64Mi  # Reduced from 256Mi
    cpu: 50m      # Reduced from 250m
```

### Ingress Not Working

```bash
# Check Traefik logs
sudo k3s kubectl logs -n kube-system -l app.kubernetes.io/name=traefik

# Verify iptables
sudo iptables -L -n | grep -E "(80|443)"

# Test locally
curl localhost:80
```

### Database Connection Issues

```bash
# Test from pod
sudo k3s kubectl run test-db --rm -it --image=postgres:15 -- \
  psql "postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require"

# Check Neon DB status
# Visit: https://console.neon.tech
```

---

## Cost Breakdown (Always Free Tier)

| Resource | Specs | Cost |
|----------|-------|------|
| Compute VM | 1 OCPU, 1GB RAM | $0 |
| Block Storage | 47GB Boot Volume | $0 |
| Bandwidth | 10TB outbound | $0 |
| Neon DB | 3GB storage | $0 |
| Let's Encrypt | SSL certificates | $0 |
| **Total** | | **$0/month** |

**Note:** Oracle Always Free includes 2 VMs. You can use second VM for staging/testing.

---

## Performance Optimization

### For 1GB RAM Instance

```yaml
# Reduce resource limits in values.yaml
resources:
  limits:
    cpu: 500m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

# Use single replica (no auto-scaling)
replicaCount: 1
```

### Enable Swap (if needed)

```bash
# On compute instance
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Security Hardening

### Disable Root SSH

```bash
sudo vim /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart sshd
```

### Setup Firewall (UFW)

```bash
sudo apt install -y ufw
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 6443/tcp
sudo ufw --force enable
```

### Enable Automatic Updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Comparison: Minikube vs Oracle Cloud K3s

| Feature | Minikube (Local) | Oracle K3s (Cloud) |
|---------|-----------------|-------------------|
| Setup Time | 5 minutes | 30 minutes |
| Image Loading | `minikube image load` | Save/transfer/import |
| Access | localhost | Public IP/domain |
| SSL/TLS | Manual | Let's Encrypt (free) |
| Uptime | Development hours | 24/7 |
| Cost | $0 | $0 (Always Free) |
| RAM | Depends on laptop | 1GB (Always Free) |
| Public Access | No | Yes |
| Production Ready | No | Yes (for MVP) |
