"""
API entrypoint: POST with user_id, login_password, report_password.
Pipeline: user lookup -> fitness rows -> decrypt (login_password) -> Excel (report_password) -> email.
"""
import logging
import sys
from datetime import date

from flask import Flask, request, jsonify

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

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/report", methods=["POST"])
def trigger_report():
    """
    Request JSON: { "user_id": int, "login_password": str, "report_password": str }
    - login_password: used only to decrypt DB data (KEK/DEK).
    - report_password: used only to password-protect the Excel file.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_id = data.get("user_id")
        login_password = data.get("login_password")
        report_password = data.get("report_password")

        if user_id is None:
            return jsonify({"success": False, "error": "user_id is required"}), 400
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "user_id must be an integer"}), 400
        if not login_password:
            return jsonify({"success": False, "error": "login_password is required"}), 400
        if not report_password:
            return jsonify({"success": False, "error": "report_password is required"}), 400

        # User lookup
        user = get_user_for_report(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        email = user.get("email")
        display_name = user.get("display_name") or "User"
        key_salt = user.get("key_salt")
        encrypted_data_key = user.get("encrypted_data_key")
        if not email or key_salt is None or encrypted_data_key is None:
            return jsonify({"success": False, "error": "User data incomplete for report"}), 400

        # Fitness rows
        rows = get_fitness_measurements(user_id)
        if not rows:
            return jsonify({"success": False, "error": "No fitness measurements found"}), 404

        # Decrypt (login_password only)
        try:
            decrypted = decrypt_fitness_rows(login_password, key_salt, encrypted_data_key, rows)
        except ValueError as e:
            return jsonify({"success": False, "error": "Decryption failed; check login_password"}), 400

        # Build Excel (report_password only)
        excel_bytes = build_report_bytes(decrypted, report_password, user_id)
        safe_name = (display_name or "User").replace(" ", "_")
        current_date = date.today().strftime("%Y-%m-%d")
        filename = f"Fitness_Report_{safe_name}_{current_date}.xlsx"

        # Send email
        send_report_email(to_email=email, display_name=display_name, excel_bytes=excel_bytes, filename=filename)

        return jsonify({"success": True, "message": "Report sent"})
    except Exception:
        logger.exception("Report failed")
        return jsonify({"success": False, "error": "Report failed"}), 500


def run_server(host="0.0.0.0", port=None):
    port = port or int(__import__("os").environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_server()
