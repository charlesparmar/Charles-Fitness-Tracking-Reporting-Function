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
| **Email draft** | `Emaildraft.md` — use this format for the email body. The name in the greeting is the **`display_name`** from the `users` table (replace `<display_name>` in the draft with that value). |
| **Encryption method (other repo)** | `encryption_method.md` — describes how the other repo encrypts data (CryptoKit/CommonCrypto). This reporting function must implement the **inverse** to decrypt: same algorithms and parameters, in Python. |
| **To be provided later** | Gmail auth token (and sender identity) |

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

## Security (critical)

- **Admin must never access user data.** The owner/admin of this reporting function must never be able to read or persist user fitness data or any password.
- **Passwords only from the trigger.** The user enters password(s) in the **other repo** when requesting the report; that repo passes them to this function. This function must **never store or log** those passwords, and must use them only in memory for the minimum time needed.
- **Two uses of the user-provided password:** (1) **Decryption** — derive KEK from password, recover DEK, decrypt measurement rows (see Decryption section below). (2) **Excel protection** — password-protect the generated workbook so only the user can open it. After both steps, **discard** the password and any in-memory decrypted data; do not log or persist.
- **Decrypted data** exists only in memory for the duration of building the Excel; then the Excel is password-protected and sent; temp files and in-memory plaintext must be cleared. No admin or logging path may expose user data.

---

## Decryption (from encryption_method.md)

The other repo encrypts data as described in **`encryption_method.md`**. This function must decrypt it using the same key hierarchy and algorithms (implemented in Python). The **password** used for decryption is the same one passed from the trigger (user enters it in the other repo when requesting the report).

### Key hierarchy (reference)

| Item | Role | Where it comes from / where stored |
|------|------|-----------------------------------|
| **KEK** (Key Encryption Key) | Protects the DEK | Derived from **password + key_salt** (not stored); derived at runtime from trigger password + user’s `key_salt` |
| **DEK** (Data Encryption Key) | Encrypts/decrypts measurement data | Stored encrypted in `users.encrypted_data_key`; recovered by decrypting with KEK |
| **Per-row nonce (IV)** | Required for AES-GCM decryption of each measurement | Stored per row in `fitness_measurements` (e.g. `encryption_iv` or equivalent column) |

### Step-by-step decryption (for this function)

1. **User row (for decryption):** From `users` for the given `user_id`, read **`key_salt`** and **`encrypted_data_key`** (in addition to `email` and `display_name`). These are required to recover the DEK. Confirm actual DB column names; `encryption_method.md` uses `key_salt` and `encrypted_data_key`.
2. **Derive KEK:** **KEK = PBKDF2(password, key_salt, 100_000, HMAC-SHA256, 32 bytes).** Use the **password from the API trigger** (same password the user will use to open the Excel). Algorithm: PBKDF2 with HMAC-SHA256; iterations: 100,000; salt: the user’s `key_salt` (decode from base64 if stored as base64); output length: 32 bytes (256-bit).
3. **Recover DEK:** Decrypt **`encrypted_data_key`** with the KEK using **AES-GCM**. The stored value is in combined GCM format (nonce + ciphertext + tag); decryption returns the raw 256-bit DEK. Use the same format/ordering as the other repo (e.g. first 12 bytes nonce, then ciphertext, then tag, or library default).
4. **Per measurement row:** For each row from `fitness_measurements` for this user:
   - Read **`encrypted_data`** (ciphertext BLOB) and the **nonce/IV** for that row (column name may be `encryption_iv` or similar; see `encryption_method.md`).
   - Decrypt with **DEK + nonce** using **AES-GCM** to get the plaintext.
   - Decode plaintext as **JSON** to get the measurement object (fields map to Excel columns: date, weight, fat_percent, bmi, fat_weight, lean_weight, neck, shoulders, biceps, forearms, chest, above_navel, waist, hips, thighs, calves).
5. **After building Excel:** Do not persist the password, KEK, DEK, or decrypted measurements; use them only in memory for building the report, then clear/discard. The generated Excel is then password-protected with the **same** trigger password and sent; only the user can open it.

### Algorithms and parameters (match the other repo)

| Component | Algorithm / parameters |
|-----------|------------------------|
| KEK derivation | PBKDF2-HMAC-SHA256; 100,000 iterations; salt = user’s `key_salt` (32 bytes); output 32 bytes |
| DEK storage | AES-GCM; decrypt `encrypted_data_key` with KEK to get DEK (combined nonce+ciphertext+tag format) |
| Measurement decryption | AES-GCM; key = DEK; nonce/IV per row from DB; ciphertext = `encrypted_data` |
| Plaintext format | JSON; decode to get measurement fields for the Excel table |

### DB columns to use (align with actual schema)

- **users:** `key_salt`, `encrypted_data_key` (and `email`, `display_name`). If the DB uses different names (e.g. `key_hash`), map them to the roles in `encryption_method.md`.
- **fitness_measurements:** `encrypted_data`; and the column that stores the per-row nonce (e.g. `encryption_iv`). If the schema uses `encryption_key_id` or similar, ensure the nonce/IV used for each row is available for AES-GCM decryption.

---

## High-Level Flow

1. **Trigger** → API (from the other repo) sends `user_id` and **password** (user enters once in the other repo). This password is used for both decryption and Excel protection; never stored or logged.
2. **User lookup** → From `users` for that `user_id`, read `email`, `display_name`, and (for decryption) `key_salt`, `encrypted_data_key`.
3. **Data extraction** → Get all rows from `fitness_measurements` where `user` = `user_id` (each row has `encrypted_data` and the per-row nonce, e.g. `encryption_iv`).
4. **Decrypt** → Using the trigger password: derive KEK (PBKDF2 + key_salt), decrypt `encrypted_data_key` to get DEK, then decrypt each row’s `encrypted_data` with DEK + nonce (AES-GCM); decode JSON to measurement fields. See **Decryption** section. Do not persist password, KEK, DEK, or plaintext.
5. **Excel report** → Build workbook from decrypted data, template structure, sort by `date` ascending, header row.
6. **Password-protect Excel** → Encrypt the workbook with the same trigger password. Use password only for this step; then discard all in-memory secrets and decrypted data.
7. **Email** → Draft per `Emaildraft.md` (greeting = `display_name`). Attach the password-protected report, send to `email`. Recipient opens the attachment with the same password.

---

## Step-by-Step Execution Plan

### Phase 1: Project structure and API trigger

| Step | Action | Notes |
|------|--------|------|
| 1.1 | Create repo structure | e.g. `src/`, `tests/`, `config/`, root script or package entrypoint. |
| 1.2 | Choose GitHub trigger mechanism | Trigger is invoked from a **different repo** (e.g. workflow or app there calls this function’s API). **Option A:** HTTP endpoint receiving POST with `user_id` and **password** (user enters in the other repo; used for data decryption and Excel protection). **Option B:** `repository_dispatch` or workflow that passes both. **Option C:** Webhook/serverless endpoint that accepts `user_id` + **password**. |
| 1.3 | Define API contract | Request: accept `user_id` (required) and **password** (required; user enters once in the other repo; used for decryption and Excel protection). Response: success/failure and optional message. Do not log or persist the password. Document in README or OpenAPI. |
| 1.4 | Add minimal HTTP handler | One route that parses `user_id` and **password**, runs the reporting pipeline (password used only for decryption and Excel encryption, then discarded), returns status. Validate inputs; return 4xx on invalid input. Never store or log the password. |

### Phase 2: Database access and user lookup

| Step | Action | Notes |
|------|--------|------|
| 2.1 | Decide DB location | Where does `Charles-Fitness-Tracker.db` live at runtime? (e.g. same host, cloud storage, attached volume.) |
| 2.2 | Add SQLite dependency | Use `sqlite3` (stdlib) or a small wrapper; no ORM required for this scope. |
| 2.3 | Implement user lookup | Query `users` for `user_id`; select `email`, `display_name`, and for decryption **`key_salt`** and **`encrypted_data_key`**. Handle “user not found” (return clear error and stop). |
| 2.4 | Store for later steps | Keep `email` and `display_name` for the email; keep `key_salt` and `encrypted_data_key` only for the decryption step (in memory; never log or persist). |

### Phase 3: Fitness data extraction and decryption

| Step | Action | Notes |
|------|--------|------|
| 3.1 | Query fitness_measurements | `SELECT` all columns from `fitness_measurements` WHERE `user` = `user_id`. Include **`encrypted_data`** and the column that stores the per-row nonce (e.g. **`encryption_iv`** — align with actual DB schema and `encryption_method.md`). Order by `date` ASC in SQL (or sort in Python). |
| 3.2 | Implement decryption (see **Decryption** section) | Use the **password from the API trigger**. (1) Derive KEK = PBKDF2(password, user’s `key_salt`, 100_000, HMAC-SHA256, 32 bytes). (2) Decrypt user’s `encrypted_data_key` with KEK (AES-GCM) to get DEK. (3) For each row, decrypt `encrypted_data` with DEK and that row’s nonce (AES-GCM). (4) Decode each plaintext as JSON. Use a dedicated module (e.g. `decrypt.py`); do not log or persist password, KEK, DEK, or decrypted content. Handle decryption failures (e.g. wrong password) with a clear error; do not expose raw data. |
| 3.3 | Map to report rows | From each decrypted JSON payload, map fields to the 16 Excel columns: `date`, `weight`, `fat_percent`, `bmi`, `fat_weight`, `lean_weight`, `neck`, `shoulders`, `biceps`, `forearms`, `chest`, `above_navel`, `waist`, `hips`, `thighs`, `calves`. |

### Phase 4: Excel report generation and password protection

| Step | Action | Notes |
|------|--------|------|
| 4.1 | Choose Excel library | Use `openpyxl` to create `.xlsx` (copy template and fill, or build from scratch). For workbook encryption, use openpyxl’s password support or a library that supports .xlsx password protection (e.g. `msoffcrypto-tool` if saving as encrypted file). |
| 4.2 | Implement report builder | One sheet named **Fitness Data**. Row 1 = header (A→P as in template structure above). Data from row 2, sorted by **date ascending**. |
| 4.3 | Password-protect workbook | Apply Excel workbook password using the **same password** from the API trigger (used earlier for decryption). Use it only for this step; do not store, log, or pass it elsewhere. After attaching to email, clear any in-memory reference to the password and decrypted data. |
| 4.4 | Naming and cleanup | Save as e.g. `report_{user_id}_{timestamp}.xlsx`. Delete temp file after email send (or retain per policy). |

### Phase 5: Email drafting and sending

| Step | Action | Notes |
|------|--------|------|
| 5.1 | Use email draft format | Body text must follow **`Emaildraft.md`**. Replace `<display_name>` in the draft with the **`display_name`** value from the `users` table (from step 2). Subject line to be defined (e.g. in config or alongside the draft). |
| 5.2 | Secure storage of secrets | Store Gmail token/credentials (and sender identity) in environment variables or a secrets manager (e.g. GitHub Secrets); never commit to repo. |
| 5.3 | Implement email sender | Use Gmail API (e.g. `google-api-python-client`) or SMTP with app password. Recipient = `email` from step 2; attach the **password-protected** Excel file; body = draft from `Emaildraft.md` with `<display_name>` replaced by the user’s `display_name`. Optionally mention in the body that the attachment is password-protected and they should use the password they entered when requesting the report. |
| 5.4 | Error handling | If send fails, log error and return failure response; optionally keep the generated file for retry or inspection. |

### Phase 6: Integration, configuration, and deployment

| Step | Action | Notes |
|------|--------|------|
| 6.1 | Wire pipeline | Single entrypoint: receive `user_id` + **password** → user lookup (including `key_salt`, `encrypted_data_key`) → fitness fetch → **decrypt** (password → KEK → DEK → decrypt rows) → Excel build → **password-protect Excel** (same password) → discard password and decrypted data → email send → return result. |
| 6.2 | Configuration | Externalise: DB path, template path (or embed template), and email config. Use env vars or a small config file (not committed). **Never** put the user’s password in config; it comes only from the API request. |
| 6.3 | Logging and idempotency | Log start/end and errors (with `user_id` only). Do **not** log or persist the password, KEK, DEK, decrypted data, or report contents. If the same `user_id` can be triggered multiple times, consider idempotency (e.g. report filename with timestamp). |
| 6.4 | Deployment | Deploy the HTTP handler (or the script invoked by GitHub Actions) to your chosen environment; ensure it has access to the DB, template, and secrets. |
| 6.5 | GitHub / trigger integration | Trigger is called from the **other repo** (user enters password there when requesting the report). Configure that trigger to pass `user_id` and **password** in the request. Test end-to-end with one user. |

---

## Suggested Project Layout (for implementation)

```
Charles-Fitness-Tracking-Reporting-Function/
├── README.md
├── ROADMAP.md                    # This file
├── Emaildraft.md                 # Email body template; <display_name> = users.display_name
├── encryption_method.md          # Encryption used by the other repo; this function implements inverse to decrypt
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

**Decryption (match encryption_method.md):** PBKDF2-HMAC-SHA256 and AES-GCM (e.g. `cryptography` or `PyCryptodome`); 100,000 iterations for KEK; 32-byte key/salt.

Stdlib: `sqlite3`, `json`, `os`, `logging`.

---

## Open Points (for you to provide later)

1. **Gmail auth** — OAuth2 token refresh flow or static token; where to store it (e.g. GitHub Secrets). Subject line and sender name/address if not in draft.
---

## Summary

| Phase | Focus |
|-------|--------|
| 1 | API trigger from other repo with `user_id` + **password** (password never stored; used for decryption + Excel) |
| 2 | DB: get `email`, `display_name`, `key_salt`, `encrypted_data_key` from `users` |
| 3 | DB: get `fitness_measurements` for `user_id`; decrypt per encryption_method.md (password → KEK → DEK → AES-GCM per row); map to Excel columns |
| 4 | Build Excel, sort by date ASC; password-protect workbook with same password; discard password and decrypted data |
| 5 | Send email to `email` with password-protected report attached |
| 6 | Wire pipeline, config, deploy, connect trigger from other repo; enforce no storage/logging of user data or password |

This roadmap is plan-only; implementation must follow **encryption_method.md** for decryption and the **Security** section so the admin never has access to user data.
