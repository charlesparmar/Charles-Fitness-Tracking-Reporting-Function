"""
SQLite Cloud database access via Weblite REST API (HTTPS).
User lookup and fitness_measurements fetch using SQLITE_DB_URL (port 8090), SQLITE_API_KEY, SQLITE_DB_NAME.
"""
import logging
from typing import Any, Dict, List, Optional

import requests
import urllib3

from src.config import SQLITE_API_KEY, SQLITE_DB_URL, SQLITE_DB_NAME, SQLITE_SSL_VERIFY

if not SQLITE_SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


def _weblite_base_url() -> str:
    """Weblite REST: G3 clusters use port 443; legacy use 8090. Preserve port from SQLITE_DB_URL."""
    url = SQLITE_DB_URL.rstrip("/")
    # G3 clusters (e.g. *.g3.sqlite.cloud) use port 443 for Weblite; do not change
    if ".g3.sqlite.cloud" in url:
        return url.rstrip("/")
    # Legacy: map 443/80 to 8090
    if ":443" in url:
        url = url.replace(":443", ":8090")
    elif ":80" in url and ":8090" not in url:
        url = url.replace(":80", ":8090")
    elif ":" not in url.split("//")[-1]:
        url = url + ":8090"
    return url.rstrip("/")


def _auth_header() -> str:
    """Bearer token for Weblite: sqlitecloud://host:8860?apikey=KEY."""
    url = SQLITE_DB_URL.rstrip("/")
    if url.startswith("https://"):
        url = url.replace("https://", "", 1)
    elif url.startswith("http://"):
        url = url.replace("http://", "", 1)
    if ":443" in url:
        url = url.replace(":443", ":8860")
    elif ":" not in url.split("/")[0]:
        url = url + ":8860"
    return f"sqlitecloud://{url}?apikey={SQLITE_API_KEY}"


def _run_query(sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """Execute SQL via Weblite POST /v2/weblite/sql; return rows as list of dicts."""
    base = _weblite_base_url()
    endpoint = f"{base}/v2/weblite/sql"
    # Weblite REST uses raw SQL; only our callers pass int (user_id) - substitute safely
    if params:
        for p in params:
            if isinstance(p, (int, float)):
                sql = sql.replace("?", str(p), 1)
            elif isinstance(p, str):
                esc = p.replace("'", "''")
                sql = sql.replace("?", f"'{esc}'", 1)
            else:
                sql = sql.replace("?", repr(p), 1)
    payload = {"sql": sql, "database": SQLITE_DB_NAME}
    resp = requests.post(
        endpoint,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_auth_header()}",
        },
        timeout=30,
        verify=SQLITE_SSL_VERIFY,
    )
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("data") or []
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    # If data is list of lists, use metadata.columns for keys
    meta = data.get("metadata", {})
    columns = meta.get("columns", [])
    names = [c.get("name", f"col{i}") for i, c in enumerate(columns)] if columns else [f"column_{i}" for i in range(len(rows[0]))]
    return [dict(zip(names, row)) for row in rows]


def get_user_for_report(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch user row for reporting: id, email, display_name, key_salt, encrypted_data_key.
    Uses users.id = user_id (API user_id maps to users.id).
    """
    sql = """
        SELECT id, email, display_name, key_salt, encrypted_data_key
        FROM users
        WHERE id = ?
    """
    rows = _run_query(sql, (user_id,))
    if not rows:
        logger.warning("User not found: user_id=%s", user_id)
        return None
    return rows[0]


def get_fitness_measurements(user_id: int) -> List[Dict[str, Any]]:
    """
    Fetch all fitness_measurements for the user, ordered by date ASC.
    Returns rows with at least: id, date, encrypted_data, encryption_iv (or iv).
    """
    sql = """
        SELECT id, user_id, week_number, date, encrypted_data, encryption_iv, created_at, source
        FROM fitness_measurements
        WHERE user_id = ?
        ORDER BY date ASC
    """
    try:
        rows = _run_query(sql, (user_id,))
    except Exception as e:
        if "user_id" in str(e) or "no such column" in str(e).lower():
            sql = """
                SELECT id, user_id, week_number, date, encrypted_data, encryption_iv, created_at, source
                FROM fitness_measurements
                WHERE user = ?
                ORDER BY date ASC
            """
            rows = _run_query(sql, (user_id,))
        else:
            raise
    for row in rows:
        if "encryption_iv" not in row and "iv" in row:
            row["encryption_iv"] = row["iv"]
    return rows
