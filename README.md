# MedGuard Backend for Vercel

This branch is a backend-only Vercel deployment target for the MedGuard FastAPI service.

## Vercel project settings

Create a separate Vercel project from this repository and use this branch as the production branch:

```text
Branch: codex/vercel-backend
Framework Preset: Other
Root Directory: /
Build Command: leave empty
Output Directory: leave empty
Install Command: leave default
```

## Required environment variables

Set these in Vercel Project Settings -> Environment Variables:

```text
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3-pro-preview
FRONTEND_URL=https://your-frontend-vercel-domain.vercel.app
```

After deployment, test:

```text
https://your-backend-vercel-domain.vercel.app/api/health
```

Then set the frontend project's `NUXT_AI_API_BASE` to the backend Vercel URL and redeploy the frontend.
