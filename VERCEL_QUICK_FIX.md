# Quick Fix for Vercel Deployment Errors

## 🚨 Emergency Troubleshooting

### Step 1: Check What Error You're Getting

Go to Vercel Dashboard → Your Project → Deployments → Click Failed Deployment

Look for these common errors:

---

## Error Type 1: "Build Failed" / Compilation Error

### Fix:

```bash
# Test build locally first
cd frontend
npm run build
```

**If local build fails:**
- Fix TypeScript errors shown
- Fix ESLint errors
- Then try deploying again

**If local build works but Vercel fails:**
- Check Node.js version in Vercel (should be 18.x or 20.x)
- Add `vercel.json`:

```json
{
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/node"
    }
  ]
}
```

---

## Error Type 2: "Environment Variables Missing"

### Fix:

Add these EXACT variables in Vercel Dashboard:

**Project Settings → Environment Variables → Add New**

```plaintext
DATABASE_URL = "Your connection string"

BETTER_AUTH_SECRET = [run: openssl rand -base64 32]

BETTER_AUTH_URL = https://your-project.vercel.app

NEXT_PUBLIC_API_URL = https://your-backend.com
(leave empty for now if backend not ready)
```

**Important:**
- Select ALL environments (Production, Preview, Development)
- Click "Add" for each variable
- Click "Redeploy" after adding

---

## Error Type 3: "Module Not Found"

### Fix:

```bash
cd frontend

# Delete and reinstall
rm -rf node_modules package-lock.json
npm install

# Try build
npm run build

# If works, commit and push
git add .
git commit -m "fix: reinstall dependencies"
git push
```

---

## Error Type 4: "Root Directory Wrong"

### Fix in Vercel:

1. Project Settings → General
2. **Root Directory**: `frontend` (not empty!)
3. Save
4. Redeploy

---

## Error Type 5: Database Connection Error

### Check:

```bash
# Test connection locally
cd frontend
node -e "console.log(process.env.DATABASE_URL)"

# Should print your connection string
```

### Fix:
- Make sure `DATABASE_URL` includes `?sslmode=require`
- Check Neon database is active
- Verify connection string is correct

---

## ⚡ Quick Deploy Checklist

Before deploying to Vercel:

```bash
# 1. Generate secret
openssl rand -base64 32
# Copy output, you'll need it!

# 2. Test build locally
cd frontend
npm run build
# ✅ Must succeed before deploying!

# 3. Commit changes
git add .
git commit -m "chore: prepare for vercel"
git push
```

In Vercel Dashboard:

1. ✅ Import repository
2. ✅ Set Root Directory: `frontend`
3. ✅ Add ALL environment variables
4. ✅ Deploy

---

## 🎯 Copy-Paste Environment Variables

**Generate secret first:**
```bash
openssl rand -base64 32
```

**Then add these in Vercel:**

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `YOUR CONNECTION STRING` |
| `BETTER_AUTH_SECRET` | [Paste output from openssl command] |
| `BETTER_AUTH_URL` | `https://your-project.vercel.app` |
| `NEXT_PUBLIC_API_URL` | Leave empty for now |

⚠️ **After first deploy, update `BETTER_AUTH_URL` with actual Vercel URL!**

---

## 🔍 Still Not Working?

### Get Specific Error Message:

1. Vercel Dashboard → Deployments
2. Click failed deployment
3. Scroll through **Build Logs**
4. Find the first RED error message
5. Copy that error

### Common Error Messages & Solutions:

| Error | Solution |
|-------|----------|
| `Cannot find module 'next'` | Run `npm install` locally, commit, push |
| `Type error: ...` | Fix TypeScript errors, or add `typescript: { ignoreBuildErrors: true }` to `next.config.ts` |
| `BETTER_AUTH_SECRET must be defined` | Add environment variable in Vercel |
| `Failed to connect to database` | Check DATABASE_URL |
| `Cannot read property of undefined` | Missing environment variable |

---

## 📱 Share Error for Help

If still stuck, share:

1. **Error message** from Vercel build logs (copy-paste)
2. **Environment variables** you added (don't share actual values!)
3. **Root directory** setting in Vercel
4. **Build command** in Vercel

Example:
```
Error: Module not found '@openai/chatkit-react'
Environment vars: DATABASE_URL, BETTER_AUTH_SECRET, BETTER_AUTH_URL ✅
Root directory: frontend ✅
Build command: npm run build ✅
```

---

## ✅ Success Indicators

Your deployment succeeded if you see:

- ✅ Green checkmark in Vercel
- ✅ "Build completed"
- ✅ Can open the URL
- ✅ Landing page loads
- ✅ Can click "Sign Up"

*Chat won't work until backend is deployed!*

---

## 🚀 After Successful Deploy

1. Copy your Vercel URL: `https://xxx.vercel.app`
2. Update `BETTER_AUTH_URL` with this URL
3. Redeploy
4. Test signup/login
5. Deploy backend next!
