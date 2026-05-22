"""One-time backfill for P1 Task 3 — peppered phone_hash + Fernet phone_ciphertext.

Walks every row of `alert_subscriptions` and `webpush_subscriptions` that
still has a plaintext `phone` value but no `phone_hash`, computes the two
new columns, and writes them back in place. After this script has run
cleanly on a database, an operator can choose to null out the legacy
`phone` column with a separate destructive step (intentionally NOT done
here so we keep an out for rollback / re-encryption with a rotated key).

Usage::

    python scripts/migrate_pii.py [--db kisanos.db]

Requires APP_PEPPER and FERNET_KEY to be set (the standard backend
environment loads them from .env via pydantic-settings).
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path

# Make `backend.*` importable when the script is run from the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cryptography.fernet import Fernet  # noqa: E402

from backend.config import get_settings  # noqa: E402


def _peppered_hash(phone: str, pepper: str) -> str:
    return hashlib.sha256((phone + pepper).encode("utf-8")).hexdigest()


def _migrate_table(conn: sqlite3.Connection, table: str, fernet: Fernet, pepper: str) -> int:
    """Backfill phone_hash + phone_ciphertext for every plaintext-only row.

    Returns the number of rows updated.
    """
    cursor = conn.execute(
        f"SELECT id, phone FROM {table} "
        f"WHERE phone IS NOT NULL AND phone != '' "
        f"AND (phone_hash IS NULL OR phone_ciphertext IS NULL)"
    )
    rows = cursor.fetchall()
    updated = 0
    for row_id, phone in rows:
        try:
            phone_hash = _peppered_hash(phone, pepper)
            phone_ct = fernet.encrypt(phone.encode("utf-8")).decode("utf-8")
        except Exception as exc:  # noqa: BLE001 — log + skip is the right call
            print(f"  skip {table}#{row_id}: {exc}", file=sys.stderr)
            continue
        conn.execute(
            f"UPDATE {table} SET phone_hash = ?, phone_ciphertext = ? WHERE id = ?",
            (phone_hash, phone_ct, row_id),
        )
        updated += 1
    conn.commit()
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", default=None,
        help="Path to the SQLite database (default: backend SQLITE_PATH).",
    )
    args = parser.parse_args()

    settings = get_settings()
    db_path = args.db or settings.SQLITE_PATH

    if not settings.APP_PEPPER or not settings.FERNET_KEY:
        print("ERROR: APP_PEPPER and FERNET_KEY must be set", file=sys.stderr)
        return 2

    fernet = Fernet(settings.FERNET_KEY.encode())

    conn = sqlite3.connect(db_path)
    try:
        alert_rows = _migrate_table(conn, "alert_subscriptions", fernet, settings.APP_PEPPER)
        webpush_rows = _migrate_table(conn, "webpush_subscriptions", fernet, settings.APP_PEPPER)
    finally:
        conn.close()

    print(
        f"Migrated {alert_rows} rows in alert_subscriptions, "
        f"{webpush_rows} rows in webpush_subscriptions"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
