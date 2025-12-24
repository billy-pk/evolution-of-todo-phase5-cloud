# Vercel Deployment Guide - Frontend Only

## 🎯 Architecture for Vercel Deployment

**Frontend (Next.js)** → Vercel ✅
**Backend (FastAPI + MCP)** → Oracle Cloud, Railway, Render, or other ❌ (Not Vercel)

> **Important**: Vercel is optimized for frontend frameworks. Your FastAPI backend and MCP server need to be deployed elsewhere.

---

## 🚀 Deployment Strategy

### Option A: Frontend on Vercel + Backend on Oracle Cloud (Recommended)
- **Frontend**: Vercel (free, global CDN)
- **Backend**: Oracle Cloud (free tier available)
- **Database**: Neon PostgreSQL (already set up)

### Option B: Frontend on Vercel + Backend on Railway/Render
- **Frontend**: Vercel
- **Backend**: Railway or Render (easy deployment)
- **Database**: Neon PostgreSQL

---

## 📋 Step-by-Step: Deploy Frontend to Vercel

### Step 1: Fix Common Deployment Issues

First, let's ensure your frontend is ready for Vercel:

#### A. Update `next.config.ts`

Your current config is minimal. Add this for better Vercel compatibility:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Ensure output is correct for Vercel
  output: 'standalone',

  // Environment variables validation
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // Disable ESLint during builds if it causes issues
  // eslint: {
  //   ignoreDuringBuilds: true,
  // },
};

export default nextConfig;
```

#### B. Check `package.json` Scripts

Your build script should be correct:
```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }
}
```

✅ This looks good!

---

### Step 2: Deploy to Vercel

#### Method 1: Via Vercel Dashboard (Easiest)

1. **Go to** [vercel.com](https://vercel.com)
2. **Sign up/Login** with GitHub
3. **Click "Add New Project"**
4. **Import** your Git repository
5. **Configure Project**:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
   - **Install Command**: `npm install`

6. **Add Environment Variables** (see Step 3 below)
7. **Click "Deploy"**

#### Method 2: Via Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Navigate to frontend
cd frontend

# Deploy
vercel

# Follow prompts:
# - Set up new project? Yes
# - Link to existing project? No
# - Project name: todo-ai-frontend
# - Which directory? ./ (current)

# For production deployment
vercel --prod
```

---

### Step 3: Environment Variables for Vercel

⚠️ **CRITICAL**: You need to add these environment variables in Vercel Dashboard.

Go to: **Project Settings → Environment Variables**

#### Required Environment Variables:

```plaintext
# 1. DATABASE_URL
# Your Neon PostgreSQL connection string
# Used by Better Auth to store users and sessions
DATABASE_URL="Your connection string"

# 2. BETTER_AUTH_SECRET
# MUST be at least 32 characters
# Generate: openssl rand -base64 32
BETTER_AUTH_SECRET=<generate-this-32-chars-minimum>

# 3. BETTER_AUTH_URL
# Your Vercel deployment URL (will be https://your-app.vercel.app)
# For now use: https://your-project-name.vercel.app
# You can update this after first deployment
BETTER_AUTH_URL=https://your-project-name.vercel.app

# 4. NEXT_PUBLIC_API_URL
# Your backend API URL (FastAPI)
# If backend not deployed yet, leave empty or use localhost for testing
# Format: https://your-backend-domain.com (NO trailing slash)
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

#### How to Add in Vercel:

1. Go to your project in Vercel Dashboard
2. Click **Settings** → **Environment Variables**
3. Add each variable:
   - **Key**: Variable name (e.g., `DATABASE_URL`)
   - **Value**: The actual value
   - **Environments**: Select all (Production, Preview, Development)
4. Click **Add** for each variable
5. Click **Save**
6. **Redeploy** your project for changes to take effect

---

### Step 4: Generate BETTER_AUTH_SECRET

```bash
# Run this command
openssl rand -base64 32

# Example output:
# kZ8p3qR6tY9wA2sD5fG8hJ0kL3mN6pQ9rT2uV5xY8zA1=

# Copy this value and use it for BETTER_AUTH_SECRET
```

⚠️ **Important**:
- Keep this secret safe
- Use the SAME secret in your backend when you deploy it
- Never commit this to Git

---

### Step 5: Update URLs After Deployment

After your first deployment, Vercel will give you a URL like:
`https://todo-ai-frontend-xyz123.vercel.app`

**Update these environment variables:**

1. **BETTER_AUTH_URL**:
   - Change from `localhost:3000`
   - To: `https://your-app.vercel.app`

2. **NEXT_PUBLIC_API_URL**:
   - Leave empty for now if backend isn't deployed
   - Or update to your backend URL when ready

**In Vercel Dashboard:**
- Settings → Environment Variables
- Edit the variables
- Redeploy

---

## 🔧 Troubleshooting Common Vercel Errors

### Error: "Build failed"

**Check:**
1. Build logs in Vercel Dashboard
2. Common issues:
   - TypeScript errors → Check `npm run build` locally
   - Missing dependencies → Check `package.json`
   - Environment variables → Make sure all are set

**Solution:**
```bash
# Test build locally first
cd frontend
npm run build

# If build works locally but fails on Vercel:
# Check Node.js version
node --version  # Should be 18.x or 20.x

# Update in vercel.json if needed
```

### Error: "Module not found"

**Solution:**
```bash
# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install

# Try build again
npm run build
```

### Error: "Environment variable is not defined"

**Solution:**
- Go to Vercel Dashboard → Settings → Environment Variables
- Make sure ALL required variables are added
- **Redeploy** the project

### Error: "Database connection failed"

**Check:**
- `DATABASE_URL` is correct
- Neon database is accessible from Vercel (it should be)
- Connection string includes `?sslmode=require`

---

## 🎨 Custom Domain (Optional)

### Add Your Own Domain

1. **Go to** Project Settings → Domains
2. **Add Domain**: `yourdomain.com`
3. **Configure DNS** at your domain registrar:
   ```
   Type: A Record
   Name: @
   Value: 76.76.21.21 (Vercel IP)

   OR

   Type: CNAME
   Name: www
   Value: cname.vercel-dns.com
   ```
4. **Wait** for DNS propagation (5-60 minutes)
5. **Update** environment variables with new domain

---

## 🚨 Backend Deployment (Next Step)

Your frontend on Vercel will work for authentication and UI, but **you still need to deploy the backend** for the chat functionality.

### Quick Backend Options:

#### Option 1: Railway (Easiest for FastAPI)
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Deploy from backend directory
cd backend
railway init
railway up
```

Railway will give you a URL like: `https://your-app.railway.app`

#### Option 2: Render
1. Go to [render.com](https://render.com)
2. Create New → Web Service
3. Connect GitHub repo
4. Select `backend` directory
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### Option 3: Oracle Cloud (Original Plan)
Follow `DEPLOYMENT.md` for full Oracle Cloud setup.

---

## 📝 Environment Variables Reference

### Frontend (Vercel)

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | Neon PostgreSQL connection string | For Better Auth user storage |
| `BETTER_AUTH_SECRET` | 32+ char random string | Generate with `openssl rand -base64 32` |
| `BETTER_AUTH_URL` | `https://your-app.vercel.app` | Your Vercel deployment URL |
| `NEXT_PUBLIC_API_URL` | `https://your-backend.com` | Backend API URL (no trailing slash) |

### Backend (Railway/Render/Oracle)

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | Neon PostgreSQL connection string | Same as frontend |
| `BETTER_AUTH_SECRET` | Same as frontend | MUST match frontend |
| `BETTER_AUTH_ISSUER` | `https://your-app.vercel.app` | Frontend URL |
| `BETTER_AUTH_JWKS_URL` | `https://your-app.vercel.app/api/auth/jwks` | JWKS endpoint |
| `OPENAI_API_KEY` | Your OpenAI API key | For AI chat |
| `MCP_SERVER_URL` | `http://localhost:8001` | MCP server URL |

---

## ✅ Deployment Checklist

### Before Deploying:

- [ ] Test build locally: `npm run build`
- [ ] Generate `BETTER_AUTH_SECRET`
- [ ] Have `DATABASE_URL` ready
- [ ] Backend deployment plan (Railway/Render/Oracle)

### During Deployment:

- [ ] Set all environment variables in Vercel
- [ ] Deploy to Vercel
- [ ] Note the Vercel URL
- [ ] Update `BETTER_AUTH_URL` with Vercel URL
- [ ] Redeploy

### After Deployment:

- [ ] Test signup/login on Vercel URL
- [ ] Deploy backend
- [ ] Update `NEXT_PUBLIC_API_URL` with backend URL
- [ ] Test chat functionality
- [ ] (Optional) Add custom domain

---

## 🆘 Still Having Issues?

### Get Detailed Error Logs:

1. **Vercel Dashboard** → Your Project → Deployments
2. Click on failed deployment
3. Check **Build Logs** and **Runtime Logs**
4. Look for specific error messages

### Common Issues & Solutions:

| Error | Solution |
|-------|----------|
| "Failed to compile" | Fix TypeScript/ESLint errors locally first |
| "Missing environment variable" | Add all variables in Vercel Dashboard |
| "Database connection error" | Check DATABASE_URL format and Neon access |
| "Better Auth error" | Ensure BETTER_AUTH_SECRET is 32+ chars |
| "API not responding" | Backend not deployed or URL incorrect |

### Test Locally First:

```bash
cd frontend

# Set environment variables
cp .env.local .env.production

# Build
npm run build

# If build succeeds, Vercel should work too
```

---

## 📚 Quick Command Reference

```bash
# Generate secret
openssl rand -base64 32

# Test build locally
cd frontend && npm run build

# Deploy to Vercel
vercel

# Deploy to production
vercel --prod

# Check deployment status
vercel ls

# View deployment logs
vercel logs [deployment-url]
```

---

## 🎯 Next Steps After Frontend is Deployed

1. ✅ Frontend deployed on Vercel
2. ⏳ Deploy backend (Railway/Render/Oracle Cloud)
3. ⏳ Update `NEXT_PUBLIC_API_URL` in Vercel
4. ⏳ Test end-to-end functionality
5. ⏳ (Optional) Add custom domain
6. ⏳ (Optional) Set up monitoring

---

**Need more help?** Share the specific error message from Vercel and I can help debug! 🚀
