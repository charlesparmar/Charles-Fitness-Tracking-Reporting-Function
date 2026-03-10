"""
Decrypt fitness measurement data per encryption_method.md.
Uses login_password only: KEK = PBKDF2(login_password, key_salt), DEK = decrypt(encrypted_data_key, KEK),
then each row: decrypt(encrypted_data, DEK, encryption_iv) -> JSON.
"""
import base64
import json
import logging
from typing import Any, Dict, List

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 100_000
KEY_BYTES = 32
GCM_NONCE_BYTES = 12
GCM_TAG_BYTES = 16


def _ensure_bytes(value: Any) -> bytes:
    """Convert base64 string, hex string (0x...), bytes, or SQLite Cloud Buffer dict to bytes."""
    if value is None:
        raise ValueError("Missing encryption value")
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("0x") or s.startswith("0X"):
            return bytes.fromhex(s[2:])
        try:
            return base64.b64decode(s)
        except Exception:
            return value.encode("utf-8")
    # SQLite Cloud Weblite returns BLOBs as {"type": "Buffer", "data": [int, ...]}
    if isinstance(value, dict) and value.get("type") == "Buffer" and "data" in value:
        return bytes(value["data"])
    raise TypeError(f"Unexpected type for encryption value: {type(value)}")


def derive_kek(login_password: str, key_salt: Any) -> bytes:
    """KEK = PBKDF2(login_password, key_salt, 100_000, HMAC-SHA256, 32 bytes)."""
    salt = _ensure_bytes(key_salt)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_BYTES,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    return kdf.derive(login_password.encode("utf-8"))


def decrypt_dek(encrypted_data_key: Any, kek: bytes) -> bytes:
    """
    Decrypt encrypted_data_key (combined GCM: nonce + ciphertext + tag) with KEK.
    CryptoKit uses 12-byte nonce, 16-byte tag.
    """
    blob = _ensure_bytes(encrypted_data_key)
    if len(blob) < GCM_NONCE_BYTES + GCM_TAG_BYTES:
        raise ValueError("encrypted_data_key too short for AES-GCM")
    nonce = blob[:GCM_NONCE_BYTES]
    tag = blob[-GCM_TAG_BYTES:]
    ciphertext = blob[GCM_NONCE_BYTES:-GCM_TAG_BYTES]
    aesgcm = AESGCM(kek)
    return aesgcm.decrypt(nonce, ciphertext + tag, None)


def decrypt_measurement_row(encrypted_data: Any, encryption_iv: Any, dek: bytes) -> Dict[str, Any]:
    """
    Decrypt one row. CryptoKit stores the combined GCM format in encrypted_data:
    nonce (12 bytes) + ciphertext + tag (16 bytes). The encryption_iv column is not used.
    """
    data = _ensure_bytes(encrypted_data)
    if len(data) < GCM_NONCE_BYTES + GCM_TAG_BYTES:
        raise ValueError(f"encrypted_data too short for AES-GCM (need nonce+ct+tag)")
    nonce = data[:GCM_NONCE_BYTES]
    ciphertext_plus_tag = data[GCM_NONCE_BYTES:]
    aesgcm = AESGCM(dek)
    plaintext = aesgcm.decrypt(nonce, ciphertext_plus_tag, None)
    return json.loads(plaintext.decode("utf-8"))


def decrypt_fitness_rows(
    login_password: str,
    key_salt: Any,
    encrypted_data_key: Any,
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Derive KEK from login_password + key_salt, recover DEK, decrypt each row.
    Returns list of decoded JSON measurement dicts (with date, weight, fat_percent, etc.).
    """
    kek = derive_kek(login_password, key_salt)
    dek = decrypt_dek(encrypted_data_key, kek)
    result = []
    for row in rows:
        enc_data = row.get("encrypted_data")
        iv = row.get("encryption_iv") or row.get("iv")
        if enc_data is None or iv is None:
            logger.warning("Skipping row missing encrypted_data or encryption_iv: id=%s", row.get("id"))
            continue
        try:
            decrypted = decrypt_measurement_row(enc_data, iv, dek)
            # Merge DB columns (date, etc.) into decrypted payload for report
            if "date" in row and decrypted.get("date") is None:
                decrypted["date"] = row["date"]
            result.append(decrypted)
        except Exception as e:
            logger.warning("Decrypt failed for row id=%s: %s", row.get("id"), e)
            raise ValueError("Decryption failed; check login_password and data.") from e
    return result
