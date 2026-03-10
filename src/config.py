"""Load configuration from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# SQLite Cloud
SQLITE_API_KEY = os.environ.get("SQLITE_API_KEY", "")
SQLITE_DB_URL = os.environ.get("SQLITE_DB_URL", "").rstrip("/")
# Weblite REST uses port 8090; optional database name (e.g. main or your-db.sqlite)
SQLITE_DB_NAME = os.environ.get("SQLITE_DB_NAME", "main")
# Set to "false" or "0" to disable SSL verification (workaround for G3 hostname mismatch on port 8090)
SQLITE_SSL_VERIFY = os.environ.get("SQLITE_SSL_VERIFY", "true").lower() not in ("false", "0", "no")

# Gmail
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_API_CREDENTIALS_PATH = os.environ.get(
    "GMAIL_API_CREDENTIALS_PATH",
    str(Path(__file__).resolve().parent.parent / "credentials.json"),
)
GMAIL_API_TOKEN_PATH = os.environ.get(
    "GMAIL_API_TOKEN_PATH",
    str(Path(__file__).resolve().parent.parent / "token.json"),
)

# Email draft and subject
EMAIL_DRAFT_PATH = Path(__file__).resolve().parent.parent / "Emaildraft.md"
REPORT_EMAIL_SUBJECT = os.environ.get("REPORT_EMAIL_SUBJECT", "Your Fitness Report from Charles' Fitness Tracker")
