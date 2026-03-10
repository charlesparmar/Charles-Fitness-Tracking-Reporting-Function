"""
CLI entrypoint to run the fitness report.
Used by GitHub Actions when triggered via workflow_dispatch (no HTTP server needed).
Reads user_id, login_password, report_password from environment.
"""
import logging
import os
import sys
from datetime import date

from src.db import get_user_for_report, get_fitness_measurements
from src.decrypt import decrypt_fitness_rows
from src.report import build_report_bytes
from src.email_sender import send_report_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run_report(user_id: int, login_password: str, report_password: str) -> None:
    """Execute the full report pipeline: fetch -> decrypt -> Excel -> email."""
    user = get_user_for_report(user_id)
    if not user:
        raise ValueError("User not found")

    email = user.get("email")
    display_name = user.get("display_name") or "User"
    key_salt = user.get("key_salt")
    encrypted_data_key = user.get("encrypted_data_key")
    if not email or key_salt is None or encrypted_data_key is None:
        raise ValueError("User data incomplete for report")

    rows = get_fitness_measurements(user_id)
    if not rows:
        raise ValueError("No fitness measurements found")

    decrypted = decrypt_fitness_rows(login_password, key_salt, encrypted_data_key, rows)
    excel_bytes = build_report_bytes(decrypted, report_password, user_id)
    safe_name = (display_name or "User").replace(" ", "_")
    current_date = date.today().strftime("%Y-%m-%d")
    filename = f"Fitness_Report_{safe_name}_{current_date}.xlsx"

    send_report_email(
        to_email=email,
        display_name=display_name,
        excel_bytes=excel_bytes,
        filename=filename,
    )
    logger.info("Report sent to %s", email)


def main() -> None:
    user_id = int(os.environ.get("USER_ID", "1"))
    login_password = os.environ.get("LOGIN_PASSWORD", "")
    report_password = os.environ.get("REPORT_PASSWORD", "")

    if not login_password or not report_password:
        logger.error("LOGIN_PASSWORD and REPORT_PASSWORD must be set")
        sys.exit(1)

    try:
        run_report(user_id, login_password, report_password)
    except ValueError as e:
        logger.error("%s", e)
        sys.exit(1)
    except Exception:
        logger.exception("Report failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
