# Trigger Fitness Report via GitHub Actions (No Deployment Needed)

The report runs **directly in GitHub Actions**. No Railway, Render, or other hosting required.

---

## Step 1: Add GitHub repository secrets

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add these as **Secrets** (not Variables) — click **New repository secret**:

### Required

| Secret | Value |
|--------|-------|
| `credentials_json` | Either **raw JSON** (paste the file contents) or **base64-encoded** (run `base64 -i credentials.json \| pbcopy` on macOS) |
| `token_json` | Either **raw JSON** (paste the file contents) or **base64-encoded** (run `base64 -i token.json \| pbcopy`) |
| `SQLITE_API_KEY` | Your SQLite Cloud API key |
| `SQLITE_DB_URL` | Your SQLite Cloud DB URL (e.g. `https://your-db.sqlitecloud.io:8090`) |

### Optional (have defaults)

| Secret | Value |
|--------|-------|
| `SQLITE_DB_NAME` | Database name (default: `main`) |
| `SQLITE_SSL_VERIFY` | `true` or `false` |
| `GMAIL_ADDRESS` | Sender email |

### For scheduled runs only

| Secret | Value |
|--------|-------|
| `USER_ID` | Default user ID (e.g. `1`) |
| `LOGIN_PASSWORD` | User's decryption password |
| `REPORT_PASSWORD` | Excel protection password |

---

## Step 2: Trigger from your iOS/macOS app

Use the GitHub API to trigger the workflow:

```
POST https://api.github.com/repos/charlesparmar/Charles-Fitness-Tracking-Reporting-Function/actions/workflows/trigger-report.yml/dispatches
```

**Headers:**
- `Authorization: Bearer <GITHUB_PAT>`
- `Accept: application/vnd.github+json`
- `X-GitHub-Api-Version: 2022-11-28`
- `Content-Type: application/json`

**Body:**
```json
{
  "ref": "main",
  "inputs": {
    "user_id": "1",
    "login_password": "user's decryption password",
    "report_password": "excel protection password"
  }
}
```

You need a **GitHub Personal Access Token (PAT)** with `workflow` scope to trigger workflows.

---

## Step 3: Manual trigger from GitHub UI

1. Go to **Actions** → **Trigger Fitness Report**
2. Click **Run workflow**
3. Enter `user_id`, `login_password`, `report_password` (or leave defaults if secrets are set)
4. Click **Run workflow**

---

## Scheduled runs

The workflow runs every **Monday at 9:00 AM UTC**. For scheduled runs, set `USER_ID`, `LOGIN_PASSWORD`, and `REPORT_PASSWORD` as secrets. To change or disable, edit the `schedule` block in `.github/workflows/trigger-report.yml`.

---

## Troubleshooting

- **`base64: invalid input`** → You may have pasted raw JSON instead of base64. The workflow now accepts both; re-run the workflow. If it still fails, ensure the secret is in **Secrets** (not Variables) and has no extra whitespace.
- **Gmail auth fails** → Ensure `credentials_json` and `token_json` contain valid OAuth file content (raw JSON or base64).
- **DB connection fails** → Check `SQLITE_API_KEY`, `SQLITE_DB_URL`, `SQLITE_DB_NAME`.
- **Decryption fails** → Verify `login_password` matches what the user used when encrypting.
