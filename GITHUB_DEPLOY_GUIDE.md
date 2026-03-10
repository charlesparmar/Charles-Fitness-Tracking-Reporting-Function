# Push to GitHub & Trigger Report via Workflow

## Step 1: Push your code to GitHub

1. **Stage and commit your changes:**
   ```bash
   cd /Users/charlesparmar/Project/Charles-Fitness-Tracking-Reporting-Function
   git add .
   git status   # Review what will be committed (.env, credentials.json, token.json should NOT appear—they're in .gitignore)
   git commit -m "Add GitHub workflow to trigger fitness report"
   ```

2. **Push to GitHub:**
   ```bash
   git push origin main
   ```
   (Use `master` instead of `main` if that's your default branch.)

---

## Step 2: Deploy the app (required for the workflow)

The workflow triggers the report by calling your app's `/report` endpoint over HTTP. You need to deploy the app first.

### Option A: Railway (recommended, free tier)

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select `Charles-Fitness-Tracking-Reporting-Function`.
3. Railway will detect Python. Add a **start command**: `gunicorn -b 0.0.0.0:$PORT src.main:app` (or use `flask run` if you add a Procfile).
4. Add a `Procfile` in your repo:
   ```
   web: gunicorn -b 0.0.0.0:$PORT src.main:app
   ```
   And add `gunicorn` to `requirements.txt`.
5. In Railway **Variables**, add all your env vars from `.env`:
   - `SQLITE_API_KEY`, `SQLITE_DB_URL`, `SQLITE_DB_NAME`, etc.
   - `GMAIL_ADDRESS`, `REPORT_EMAIL_SUBJECT`
6. For Gmail OAuth: upload `credentials.json` and `token.json` as file variables, or bake them into the deploy (see Railway docs for secrets).
7. Deploy. Copy the public URL (e.g. `https://your-app.railway.app`).

### Option B: Render

1. Go to [render.com](https://render.com) → **New** → **Web Service**.
2. Connect your GitHub repo.
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn -b 0.0.0.0:$PORT src.main:app`
5. Add environment variables (same as `.env`).
6. Deploy and copy the service URL.

### Option C: Google Cloud Run

1. Use `gcloud run deploy` with a Dockerfile or Cloud Build.
2. Set env vars in the Cloud Run service.
3. Copy the service URL.

---

## Step 3: Add GitHub repository secrets

1. Open your repo on GitHub: `https://github.com/charlesparmar/Charles-Fitness-Tracking-Reporting-Function`
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

| Secret Name       | Value                                                                 |
|-------------------|-----------------------------------------------------------------------|
| `REPORT_API_URL`  | Base URL of your deployed app (e.g. `https://your-app.railway.app`)    |
| `USER_ID`         | Default user ID for scheduled runs (e.g. `1`)                         |
| `LOGIN_PASSWORD`  | User's login password (for decryption)                                |
| `REPORT_PASSWORD` | Password to protect the Excel file                                    |

For **manual runs**, you can enter these in the workflow form instead. For **scheduled runs**, all four secrets must be set.

---

## Step 4: Run the workflow

### Manual trigger

1. Go to **Actions** → **Trigger Fitness Report**
2. Click **Run workflow**
3. Fill in (or leave default):
   - **User ID**: e.g. `1`
   - **Login password**: user's decryption password
   - **Report password**: Excel protection password
4. Click **Run workflow**

### Scheduled runs

The workflow is set to run every **Monday at 9:00 AM UTC**. For scheduled runs, it uses the secrets `USER_ID`, `LOGIN_PASSWORD`, and `REPORT_PASSWORD`.

To change or disable the schedule, edit `.github/workflows/trigger-report.yml` and modify or remove the `schedule` block.

---

## Troubleshooting

- **"REPORT_API_URL secret is not set"** → Add the `REPORT_API_URL` secret with your deployed app URL.
- **404 / connection refused** → Check that the app is deployed and the URL is correct (no trailing slash).
- **401 / 500 from /report** → Check app logs on Railway/Render; verify DB and Gmail credentials.
- **Gmail auth issues** → Ensure `credentials.json` and `token.json` are available in the deployed environment (e.g. as build-time secrets or file variables).
