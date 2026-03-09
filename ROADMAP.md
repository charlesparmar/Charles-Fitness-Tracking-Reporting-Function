# Roadmap: Fitness Reporting Function

Python-based reporting function that is triggered via GitHub API, fetches user and fitness data from SQLite, decrypts measurements, generates an Excel report, password-protects it with a user-supplied password from the trigger, and emails it. Only the user can open the report (app owner/admin never has the password).

---

## Reference Materials

| Item | Description |
|------|-------------|
| **Database** | SQLite: `Charles-Fitness-Tracker.db` |
| **Users table** | Columns used: `user_id` (identifier), `email`, `display_name` |
| **Fitness table** | `fitness_measurements`: `id`, `week_number`, `date`, `encrypted_data`, `encryption_key_id`, `created_at`, `source_url`, `user` (FK to user_id) |
| **Excel template** | `~/Downloads/tmp467pf_9d.xlsx` — structure defined below |
| **Report password** | Supplied by the user in the API trigger each time (from the other repo). Used only to password-protect the Excel; never stored or logged. App owner/admin cannot open the report. |
| **To be provided later** | Decryption method; Gmail auth token and email draft details |

#### Excel template structure (tmp467pf_9d.xlsx)

- **Sheet name:** `Fitness Data`
- **Row 1 = header.** Columns A→P:

| Col | Header       | Col | Header       |
|-----|--------------|-----|--------------|
| A   | date         | I   | biceps       |
| B   | weight       | J   | forearms     |
| C   | fat_percent  | K   | chest        |
| D   | bmi          | L   | above_navel  |
| E   | fat_weight   | M   | waist        |
| F   | lean_weight  | N   | hips         |
| G   | neck         | O   | thighs       |
| H   | shoulders    | P   | calves       |

- **Data:** From row 2. Column A = date (e.g. DD-MM-YYYY or YYYY-MM-DD); B–P = numeric.
- **Output order:** Sort by `date` **ascending** (oldest on top, newest at bottom).

---

## High-Level Flow

1. **Trigger** → GitHub API (trigger from the other repo) sends `user_id` and **report password** (user enters password each time).
2. **User lookup** → Read `email` and `display_name` from `users` for that `user_id`.
3. **Data extraction** → Get all rows from `fitness_measurements` where `user` = `user_id`.
4. **Decrypt** → Apply your decryption method to `encrypted_data` (and keys if needed).
5. **Excel report** → Build workbook matching template structure, sort by `date` ascending, add header row.
6. **Password-protect Excel** → Encrypt the workbook with the report password from the trigger. Do not store or log the password; discard after use.
7. **Email** → Draft message using your details, attach the password-protected report, send to the extracted `email`. Recipient opens the attachment and enters the same password to view the report.

---

## Step-by-Step Execution Plan

### Phase 1: Project structure and API trigger

| Step | Action | Notes |
|------|--------|------|
| 1.1 | Create repo structure | e.g. `src/`, `tests/`, `config/`, root script or package entrypoint. |
| 1.2 | Choose GitHub trigger mechanism | Trigger is invoked from a **different repo** (e.g. workflow or app there calls this function’s API). **Option A:** HTTP endpoint receiving POST with `user_id` and `report_password`. **Option B:** `repository_dispatch` or workflow that passes both in the request. **Option C:** Webhook/serverless endpoint that accepts `user_id` + `report_password`. |
| 1.3 | Define API contract | Request: accept `user_id` (required) and `report_password` (required; user enters each time in the other repo). Response: success/failure and optional message. Do not log or persist `report_password`. Document in README or OpenAPI. |
| 1.4 | Add minimal HTTP handler | One route that parses `user_id` and `report_password`, runs the reporting pipeline (passing password only into Excel encryption step), returns status. Validate inputs; return 4xx on invalid input. Never store or log the password. |

### Phase 2: Database access and user lookup

| Step | Action | Notes |
|------|--------|------|
| 2.1 | Decide DB location | Where does `Charles-Fitness-Tracker.db` live at runtime? (e.g. same host, cloud storage, attached volume.) |
| 2.2 | Add SQLite dependency | Use `sqlite3` (stdlib) or a small wrapper; no ORM required for this scope. |
| 2.3 | Implement user lookup | Query `users` for `user_id`; select `email` and `display_name`. Handle “user not found” (e.g. return clear error to API and stop). |
| 2.4 | Store for later steps | Keep `email` and `display_name` in memory (or pass through pipeline) for Excel metadata and email recipient/subject/body. |

### Phase 3: Fitness data extraction and decryption

| Step | Action | Notes |
|------|--------|------|
| 3.1 | Query fitness_measurements | `SELECT` all columns from `fitness_measurements` WHERE `user` = `user_id`. Order by `date` ASC in SQL (or sort in Python). |
| 3.2 | Integrate decryption | Once you provide the decryption method: add a decryption module/function that takes `encrypted_data` (and `encryption_key_id` / user keys if needed) and returns plaintext (e.g. JSON or structured dict). Handle decryption failures (log and skip or fail the run). |
| 3.3 | Map to report rows | From decrypted payload, map fields to the 16 Excel columns: `date`, `weight`, `fat_percent`, `bmi`, `fat_weight`, `lean_weight`, `neck`, `shoulders`, `biceps`, `forearms`, `chest`, `above_navel`, `waist`, `hips`, `thighs`, `calves`. |

### Phase 4: Excel report generation and password protection

| Step | Action | Notes |
|------|--------|------|
| 4.1 | Choose Excel library | Use `openpyxl` to create `.xlsx` (copy template and fill, or build from scratch). For workbook encryption, use openpyxl’s password support or a library that supports .xlsx password protection (e.g. `msoffcrypto-tool` if saving as encrypted file). |
| 4.2 | Implement report builder | One sheet named **Fitness Data**. Row 1 = header (A→P as in template structure above). Data from row 2, sorted by **date ascending**. |
| 4.3 | Password-protect workbook | Apply Excel workbook password using the `report_password` from the API trigger. Use it only for this step; do not store, log, or pass it elsewhere. After attaching to email, clear any in-memory reference to the password. |
| 4.4 | Naming and cleanup | Save as e.g. `report_{user_id}_{timestamp}.xlsx`. Delete temp file after email send (or retain per policy). |

### Phase 5: Email drafting and sending

| Step | Action | Notes |
|------|--------|------|
| 5.1 | Receive email details | You will provide: Gmail auth token (or OAuth2 credentials), sender identity, and email draft (subject/body template). |
| 5.2 | Secure storage of secrets | Store token/credentials in environment variables or a secrets manager (e.g. GitHub Secrets); never commit to repo. |
| 5.3 | Implement email sender | Use Gmail API (e.g. `google-api-python-client`) or SMTP with app password. Function: recipient = `email` from step 2; attach the **password-protected** Excel file; fill subject/body from draft (e.g. substitute `{display_name}`). Optionally mention in the email body that the attachment is password-protected and the user should use the password they entered when requesting the report. |
| 5.4 | Error handling | If send fails, log error and return failure response; optionally keep the generated file for retry or inspection. |

### Phase 6: Integration, configuration, and deployment

| Step | Action | Notes |
|------|--------|------|
| 6.1 | Wire pipeline | Single entrypoint: receive `user_id` + `report_password` → user lookup → fitness fetch → decrypt → Excel build → password-protect Excel (use password, then discard) → email send → return result. |
| 6.2 | Configuration | Externalise: DB path, template path (or embed template), decryption params, and email config. Use env vars or a small config file (not committed). Never put `report_password` in config; it comes only from the request. |
| 6.3 | Logging and idempotency | Log start/end and errors (with `user_id` only). Do **not** log or persist `report_password` or report contents. If the same `user_id` can be triggered multiple times, consider idempotency (e.g. report filename with timestamp). |
| 6.4 | Deployment | Deploy the HTTP handler (or the script invoked by GitHub Actions) to your chosen environment; ensure it has access to the DB, template, and secrets. |
| 6.5 | GitHub / trigger integration | Trigger is called from the **other repo** (user enters password there each time). Configure that trigger to pass `user_id` and `report_password` in the request. Test end-to-end with one user. |

---

## Suggested Project Layout (for implementation)

```
Charles-Fitness-Tracking-Reporting-Function/
├── README.md
├── ROADMAP.md                    # This file
├── requirements.txt              # e.g. openpyxl, google-api-python-client, etc.
├── config/
│   └── .env.example              # Template for DB path, secrets (no real secrets)
├── src/
│   ├── __init__.py
│   ├── main.py                   # API entrypoint or CLI that runs the pipeline
│   ├── db.py                     # SQLite connection, user lookup, fitness fetch
│   ├── decrypt.py                # Decryption (to be implemented with your method)
│   ├── report.py                 # Excel generation using template structure
│   └── email_sender.py           # Draft and send email with attachment
├── tests/
│   └── ...                       # Unit tests for each module where possible
└── .github/
    └── workflows/
        └── trigger-report.yml    # Optional: workflow that calls the function
```

---

## Dependencies to Add (when implementing)

- **Excel:** `openpyxl`; for workbook password protection, openpyxl or a library that supports .xlsx encryption (e.g. `msoffcrypto-tool`) as needed
- **Gmail:** `google-auth`, `google-api-python-client` (or `smtplib` + app password)
- **HTTP (if serverless):** `flask` or `fastapi` (or platform’s built-in handler)
- **Config:** `python-dotenv` optional

Stdlib: `sqlite3`, `json`, `os`, `logging`.

---

## Open Points (for you to provide later)

1. **Decryption method** — Algorithm, key derivation, and how `encryption_key_id` / user keys (e.g. from `users`) are used.
2. **Gmail auth** — OAuth2 token refresh flow or static token; where to store it (e.g. GitHub Secrets).
3. **Email draft** — Subject line template, body template (e.g. “Hi {display_name}, …”), and sender name/address.
---

## Summary

| Phase | Focus |
|-------|--------|
| 1 | API trigger from other repo with `user_id` + `report_password` (password never stored) |
| 2 | DB: get `email` and `display_name` from `users` |
| 3 | DB: get all `fitness_measurements` for `user_id`; decrypt rows |
| 4 | Build Excel, sort by date ASC; password-protect workbook with `report_password`; discard password |
| 5 | Send email to `email` with password-protected report attached |
| 6 | Wire pipeline, config, deploy, and connect trigger from other repo |

This roadmap is plan-only; implementation will follow in a later phase once decryption and email details are provided.
