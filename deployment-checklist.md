# LoanSense Deployment Checklist

Use this guide when deploying LoanSense to production (Railway for Backend, Vercel for Frontend).

## 1. Backend API (Railway/Render)

### Environment Variables
Before triggering the deployment, ensure these environment variables are set in your Railway dashboard:

- `DATABASE_URL`: Your managed PostgreSQL connection string (e.g. `postgresql://user:pass@host/dbname`)
- `GEMINI_API_KEY`: Your Groq/Gemini API key for the LLM agent
- `MLFLOW_TRACKING_URI`: Leave blank or set to `sqlite:////app/mlruns/mlflow.db` to use the bundled models.
- `ENVIRONMENT`: `production`
- `FRONTEND_URL`: Your exact Vercel URL (e.g. `https://loansense-demo.vercel.app`) - **Required for CORS!**

### Deployment Steps
- [ ] Ensure `.env` is securely in `.dockerignore` and `.gitignore`.
- [ ] Connect your GitHub repo to Railway.
- [ ] Select the `backend/Dockerfile` as the build source (Railway should auto-detect this via `railway.json`).
- [ ] Wait for build to complete. The build will run `patch_mlflow_paths.py` to fix Windows pathing.
- [ ] Once deployed, run Database migrations if using a fresh DB:
  *(You can run this via Railway's CLI or deployment bash command)*
  ```bash
  alembic upgrade head
  ```

### Health Check
- [ ] Visit `https://<YOUR-RAILWAY-URL>/api/v1/health`. Ensure you receive a `{"status":"healthy"}` JSON with models listed as `loaded`.

---

## 2. Frontend SPA (Vercel)

### Environment Variables
Set this in the Vercel dashboard:
- `VITE_API_URL`: Your live Railway API URL (e.g. `https://loansense-backend.up.railway.app/api/v1`)

### Deployment Steps
- [ ] Connect repo to Vercel.
- [ ] Set Framework Preset to `Vite`.
- [ ] Ensure Build Command is `npm run build` and Output Directory is `dist`.
- [ ] Deploy.

---

## 3. Post-Deployment E2E Validation
- [ ] Open the Vercel URL.
- [ ] Submit a test application via the Dashboard.
- [ ] Verify the Verdict is generated successfully.
- [ ] Run the warmup script from your local machine to ping the live URL before any demos:
  ```bash
  python backend/scripts/warmup.py <YOUR-RAILWAY-URL>
  ```
