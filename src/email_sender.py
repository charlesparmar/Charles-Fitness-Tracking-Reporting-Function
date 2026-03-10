"""
Send the fitness report email via Gmail API (OAuth2).
Uses credentials.json and token.json; body from Emaildraft.md with <display_name> replaced.
"""
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from src.config import (
    GMAIL_ADDRESS,
    GMAIL_API_CREDENTIALS_PATH,
    GMAIL_API_TOKEN_PATH,
    EMAIL_DRAFT_PATH,
    REPORT_EMAIL_SUBJECT,
)

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_credentials() -> Credentials:
    """Load or refresh Gmail OAuth2 credentials."""
    creds = None
    token_path = Path(GMAIL_API_TOKEN_PATH)
    creds_path = Path(GMAIL_API_CREDENTIALS_PATH)
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                # Token expired or revoked; run OAuth flow to get new token
                creds = None
        if not creds:
            if not creds_path.exists():
                raise FileNotFoundError(f"Gmail credentials not found: {creds_path}")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def get_email_body(display_name: str) -> str:
    """Load Emaildraft.md and replace <display_name> with the user's display_name."""
    path = Path(EMAIL_DRAFT_PATH)
    if not path.exists():
        return f"Hello {display_name}\n\nPlease find your fitness data attached."
    text = path.read_text(encoding="utf-8")
    return text.replace("<display_name>", display_name)


def send_report_email(
    to_email: str,
    display_name: str,
    excel_bytes: bytes,
    filename: str = "fitness_report.xlsx",
) -> None:
    """
    Send email to to_email with body from draft (display_name substituted),
    subject from config, and Excel file attached. Uses Gmail API.
    """
    creds = get_gmail_credentials()
    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart()
    msg["To"] = to_email
    msg["From"] = GMAIL_ADDRESS
    msg["Subject"] = REPORT_EMAIL_SUBJECT
    body = get_email_body(display_name)
    msg.attach(MIMEText(body, "plain"))

    part = MIMEApplication(excel_bytes, _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info("Report email sent to %s", to_email)
