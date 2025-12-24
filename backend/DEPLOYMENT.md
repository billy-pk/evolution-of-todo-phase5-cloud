# Backend Deployment Guide

This guide covers deploying the backend in two different modes:
1. **Unified Deployment** (Render): Single service with MCP server mounted on FastAPI
2. **Separate Deployment** (OCI): Two separate services running independently

## Deployment Modes

### Mode 1: Unified Deployment (Render, Heroku, Railway, etc.)

In this mode, the MCP server is mounted on the FastAPI application as a sub-app. This is ideal for platforms that charge per service or where you want simpler deployment.

**Configuration:**

```bash
# .env or environment variables
MOUNT_MCP_SERVER=true
MCP_SERVER_URL=  # Leave empty for auto-detection
```

**How it works:**
- FastAPI starts on port 8000 (or `$PORT` on Render)
- MCP server is automatically mounted at `/mcp` endpoint
- Agent connects to `http://localhost:8000/mcp` (or your deployed URL)
- **Single process handles both REST API and MCP requests**

**Deployment steps for Render:**

1. Create a new Web Service on Render
2. Connect your repository
3. Set **Root Directory**: `backend` (important!)
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
   ```
   DATABASE_URL=<your-neon-postgresql-url>
   BETTER_AUTH_SECRET=<your-secret>
   BETTER_AUTH_URL=<your-frontend-url>
   OPENAI_API_KEY=<your-openai-key>
   MOUNT_MCP_SERVER=true
   ENVIRONMENT=production
   ```

7. Deploy

**Verifying deployment:**
- Check health: `https://your-app.onrender.com/health`
- Check MCP endpoint: `https://your-app.onrender.com/mcp` (should return MCP server info)

---

### Mode 2: Separate Deployment (OCI, AWS, DigitalOcean, etc.)

In this mode, the FastAPI backend and MCP server run as separate services. This is ideal for:
- Container orchestration (Kubernetes, Docker Compose)
- Separate scaling of REST API vs MCP tools
- Multi-cloud deployments

**Configuration:**

**Backend service (.env):**
```bash
MOUNT_MCP_SERVER=false
MCP_SERVER_URL=http://mcp-service:8001/mcp  # Or wherever MCP is hosted
```

**MCP service (.env):**
```bash
DATABASE_URL=<your-neon-postgresql-url>
# No MOUNT_MCP_SERVER needed for standalone server
```

**How it works:**
- FastAPI runs on port 8000 (REST API endpoints)
- MCP server runs separately on port 8001 (`python tools/server.py`)
- Agent connects to MCP server via `MCP_SERVER_URL`
- **Two separate processes/containers**

**Deployment steps for OCI:**

1. **Backend service:**
   - Create compute instance or container
   - Install dependencies: `pip install -r requirements.txt`
   - Set environment variables (see above)
   - Start: `uvicorn main:app --host 0.0.0.0 --port 8000`

2. **MCP service:**
   - Create separate compute instance or container
   - Install dependencies: `pip install -r requirements.txt`
   - Set DATABASE_URL environment variable
   - Start: `cd tools && python server.py`
   - Server will run on port 8001

3. **Networking:**
   - Ensure MCP service port 8001 is accessible from backend service
   - Update `MCP_SERVER_URL` in backend to point to MCP service
   - Example: `MCP_SERVER_URL=http://10.0.1.5:8001/mcp`

**Docker Compose example:**

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - MOUNT_MCP_SERVER=false
      - MCP_SERVER_URL=http://mcp-server:8001/mcp
    command: uvicorn main:app --host 0.0.0.0 --port 8000

  mcp-server:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=${DATABASE_URL}
    working_dir: /app/tools
    command: python server.py
```

---

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | Neon PostgreSQL connection string |
| `BETTER_AUTH_SECRET` | Yes | - | Shared secret with frontend |
| `BETTER_AUTH_URL` | Yes | - | Frontend URL for JWKS endpoint |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `MOUNT_MCP_SERVER` | No | `false` | `true` = unified, `false` = separate |
| `MCP_SERVER_URL` | No | Auto | Override MCP server URL |
| `ENVIRONMENT` | No | `development` | `production` or `development` |
| `API_HOST` | No | `0.0.0.0` | API bind address |
| `API_PORT` | No | `8000` | API port (use `$PORT` on Render) |

---

## Troubleshooting

### Unified mode: "MCP server not responding"

1. Check logs for MCP mounting: Should see "✅ MCP server mounted at /mcp"
2. Test endpoint: `curl http://localhost:8000/mcp`
3. Verify `MOUNT_MCP_SERVER=true` in environment

### Separate mode: "Connection refused to MCP server"

1. Ensure MCP server is running: `cd tools && python server.py`
2. Check MCP server logs: Should see "Server running on port 8001"
3. Test MCP endpoint: `curl http://localhost:8001/mcp`
4. Verify `MCP_SERVER_URL` points to correct host:port

### Database connection errors

1. Check `DATABASE_URL` format: `postgresql://user:pass@host/dbname?sslmode=require`
2. Verify database is accessible from deployment environment
3. Check `/health` endpoint for database status

### CORS errors from frontend

1. Update CORS origins in `main.py` to include your production frontend URL
2. For Render deployments, add: `https://your-frontend.vercel.app`

---

## Production Checklist

- [ ] Set strong `BETTER_AUTH_SECRET` (min 32 characters)
- [ ] Use production database (Neon, RDS, etc.)
- [ ] Configure CORS for production frontend URL
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting appropriately
- [ ] Test health endpoint returns database connected
- [ ] Verify JWT authentication works end-to-end
- [ ] Test chat functionality with MCP tools

---

## Quick Start Commands

**Local development (separate mode - default):**
```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: MCP Server
cd backend/tools
python server.py
```

**Local development (unified mode):**
```bash
# .env
echo "MOUNT_MCP_SERVER=true" >> .env

# Single terminal
cd backend
uvicorn main:app --reload --port 8000
```

---

## Migration Guide

### From Separate to Unified (for Render deployment)

1. Update `.env`: `MOUNT_MCP_SERVER=true`
2. Remove `MCP_SERVER_URL` or set to empty
3. Stop standalone MCP server (no longer needed)
4. Restart backend: `uvicorn main:app --reload`
5. Verify logs show: "✅ MCP server mounted at /mcp"

### From Unified to Separate (for OCI deployment)

1. Update `.env`: `MOUNT_MCP_SERVER=false`
2. Set `MCP_SERVER_URL=http://localhost:8001/mcp`
3. Start MCP server separately: `cd tools && python server.py`
4. Restart backend: `uvicorn main:app --reload`
5. Verify logs show: "ℹ️ MCP server not mounted - expecting separate service on port 8001"
