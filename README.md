# Fitness Reporting Function

Python service that generates password-protected fitness reports and emails them. Triggered via HTTP POST with `user_id`, `login_password`, and `report_password`.

## Setup

1. **Create and activate the virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   - Copy `config/.env.example` to `.env` in the project root (or set env vars).
   - Set `SQLITE_API_KEY`, `SQLITE_DB_URL`, `GMAIL_ADDRESS`, `GMAIL_API_CREDENTIALS_PATH`, `GMAIL_API_TOKEN_PATH`.

3. **Gmail OAuth**
   - Place `credentials.json` (from Google Cloud Console) in the project root.
   - On first send, the app will open a browser to complete OAuth and save `token.json`.

## Run the API server

From the project root:

```bash
source .venv/bin/activate
export PYTHONPATH=.
python -m src.main
```

Server listens on `http://0.0.0.0:5000` by default. Set `PORT` (e.g. `PORT=5050`) if 5000 is in use.

## API

- **GET /health** — Health check.
- **POST /report** — Generate and email the report.

  **Request body (JSON):**
  - `user_id` (int, required)
  - `login_password` (str, required) — Used only to decrypt DB data. Never stored or logged.
  - `report_password` (str, required) — Used only to password-protect the Excel file. Recipient enters this to open the attachment.

  **Example:**
  ```bash
  curl -X POST http://localhost:5000/report \
    -H "Content-Type: application/json" \
    -d '{"user_id": 1, "login_password": "your_login_password", "report_password": "your_excel_password"}'
  ```

  **Responses:** `200` with `{"success": true, "message": "Report sent"}`, or `4xx/5xx` with `{"success": false, "error": "..."}`.

## Security

- `login_password` and `report_password` are never stored or logged.
- Decryption uses only `login_password`; Excel protection uses only `report_password`.
- Admin of this service cannot open user data or the report file without the user’s passwords.

See [ROADMAP.md](ROADMAP.md) and [encryption_method.md](encryption_method.md) for full design and encryption details.
