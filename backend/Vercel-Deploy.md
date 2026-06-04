# Vercel Deploy Guide

1. Create a new project in Vercel and connect your Git repository.
2. In the Project Settings -> Environment Variables, add the values from `.env.example`.
   - Set `OAUTH_CALLBACK_BASE` to `https://<your-vercel-deployment>.vercel.app`.
3. Ensure `vercel.json` is present (routes `/api/*` to the Python entrypoint).
4. Deploy. After deployment, confirm that `/api/v1/auth/ping` returns `{ "ok": true }`.
5. In your OAuth provider dashboards (Google/GitHub/LinkedIn), configure the redirect URIs to:
   - `https://<your-vercel-deployment>.vercel.app/api/v1/auth/oauth/google/callback`
   - `https://<your-vercel-deployment>.vercel.app/api/v1/auth/oauth/github/callback`
   - `https://<your-vercel-deployment>.vercel.app/api/v1/auth/oauth/linkedin/callback`

Testing tips
- Use the browser frontend hosted on GitHub Pages or locally. If GitHub Pages, set `data-api-base-fallback` in `index.html` to `https://<your-vercel-deployment>.vercel.app`.
- To run locally with OAuth providers, you can set `OAUTH_CALLBACK_BASE` to `http://localhost:8000` and configure provider redirect URIs accordingly (some providers allow localhost redirects).

