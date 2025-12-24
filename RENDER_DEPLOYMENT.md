# Render 2-Service Deployment Guide

This guide explains how to deploy the Evolution of Todo app with 2 separate services on Render.

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│   Frontend  │─────▶│  Backend (8000)  │─────▶│  MCP Server │
│  (Vercel)   │      │   FastAPI App    │      │   (8001)    │
└─────────────┘      └──────────────────┘      └─────────────┘
                              │                        │
                              ▼                        ▼
                         ┌──────────────────────────────┐
                         │    Neon PostgreSQL DB        │
                         └──────────────────────────────┘
```

## Why 2 Services?

**Problem**: Single-service deployment with mounted MCP causes HTTP deadlock when the server tries to make requests to itself.

**Solution**: Deploy MCP as a separate service so the backend can make HTTP requests to it without blocking.

## Deployment Options

### Option A: Using render.yaml (Recommended)

1. **Push to GitHub**:
   ```bash
   git add render.yaml backend/tools/mcp_standalone.py RENDER_DEPLOYMENT.md
   git commit -m "Add 2-service Render configuration"
   git push origin main
   ```

2. **Create Blueprint in Render**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository with `render.yaml`
   - Render will create **both services** automatically

3. **Set Environment Variables**:

   For **evolution-todo-backend**:
   ```
   DATABASE_URL=postgresql://user:pass@host/db
   BETTER_AUTH_SECRET=your-secret-key
   BETTER_AUTH_URL=https://your-frontend.vercel.app
   OPENAI_API_KEY=sk-...
   ```

   For **evolution-todo-mcp**:
   ```
   DATABASE_URL=postgresql://user:pass@host/db
   ```

   Note: `MCP_SERVER_URL` is auto-generated from the MCP service host.

### Option B: Manual Service Creation

If you prefer to create services manually:

#### Service 1: Backend
- **Name**: evolution-todo-backend
- **Type**: Web Service
- **Runtime**: Python
- **Build Command**: `cd backend && pip install -r requirements.txt`
- **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**: See Option A

#### Service 2: MCP Server
- **Name**: evolution-todo-mcp
- **Type**: Web Service
- **Runtime**: Python
- **Build Command**: `cd backend && pip install -r requirements.txt`
- **Start Command**: `cd backend && python tools/mcp_standalone.py`
- **Environment Variables**:
  - `DATABASE_URL` (same as backend)
  - `PORT=8001`

#### Link Services
In backend environment variables, add:
```
MCP_SERVER_URL=https://evolution-todo-mcp.onrender.com/mcp
```

## Verification

### 1. Check MCP Server Health
```bash
curl https://evolution-todo-mcp.onrender.com/mcp
```
Should return MCP server info.

### 2. Check Backend Health
```bash
curl https://evolution-todo-backend.onrender.com/health
```
Should return:
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "connected"
}
```

### 3. Check Logs
- Backend logs should show: `ℹ️  MCP server not mounted - expecting separate service on port 8001`
- MCP logs should show: `🚀 Starting standalone MCP server on 0.0.0.0:8001`

## Costs

- **Free Tier**: Both services run on free tier (total: $0/month)
- **Paid**: Both services on Starter tier (total: $14/month)

Note: Free tier services spin down after inactivity. First request may be slow.

## Updating MCP_SERVER_URL After Deployment

After both services are deployed, update the backend's `MCP_SERVER_URL`:

1. Get the MCP service URL from Render dashboard (e.g., `https://evolution-todo-mcp.onrender.com`)
2. In backend service, set: `MCP_SERVER_URL=https://evolution-todo-mcp.onrender.com/mcp`
3. Backend will restart automatically

## Troubleshooting

### Backend can't connect to MCP
- Check `MCP_SERVER_URL` is set correctly
- Verify MCP service is running (not sleeping)
- Check MCP service logs for errors

### MCP Server database errors
- Ensure `DATABASE_URL` is set in MCP service
- Verify database is accessible from both services

### Chat not working
- Check both services are running
- Verify `BETTER_AUTH_URL` points to frontend
- Check OpenAI API key is valid
- Look for errors in both service logs

## Local Development

For local development, run both services:

**Terminal 1 - Backend**:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - MCP Server**:
```bash
cd backend
python tools/mcp_standalone.py
```

Set in backend `.env`:
```
MOUNT_MCP_SERVER=false
MCP_SERVER_URL=http://localhost:8001/mcp
```

## Migration from Single Service

If you had a single-service deployment, follow these steps:

1. Deploy using render.yaml (creates both services)
2. Update frontend to point to new backend URL
3. Delete old single-service deployment
4. Verify chat functionality works

## Next Steps

After deployment:
1. Update frontend `NEXT_PUBLIC_API_URL` to point to backend service
2. Update backend `BETTER_AUTH_URL` to point to frontend
3. Test chat functionality
4. Monitor both services for any errors
