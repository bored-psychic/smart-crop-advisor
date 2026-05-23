"""initial schema — baseline capturing full schema after P0 + P1

Revision ID: 0001
Revises:
Create Date: 2026-05-22

This is a hand-written baseline migration.  It captures every table and index
that exists after the P0 and P1 remediation passes, including the PII-at-rest
columns (phone_hash, phone_ciphertext) introduced in P1 Task 3 and the
preferred_lang column managed previously by an inline ALTER TABLE in db.py.

Because the database may already contain this schema, all DDL statements use
IF NOT EXISTS so that applying this migration to a freshly initialised DB and
to an existing production DB both succeed without error.
"""

from alembic import op

# revision identifiers used by Alembic
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── alert_subscriptions ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS alert_subscriptions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            phone            TEXT,
            phone_hash       TEXT,
            phone_ciphertext TEXT,
            district         TEXT,
            state            TEXT    NOT NULL,
            crops            TEXT    NOT NULL DEFAULT '[]',
            alert_types      TEXT    NOT NULL DEFAULT '["frost","heavy_rain","pest_risk"]',
            active           INTEGER NOT NULL DEFAULT 1,
            preferred_lang   TEXT    NOT NULL DEFAULT 'en',
            created_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── webpush_subscriptions ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS webpush_subscriptions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            phone            TEXT,
            phone_hash       TEXT,
            phone_ciphertext TEXT,
            endpoint         TEXT NOT NULL UNIQUE,
            p256dh           TEXT NOT NULL,
            auth             TEXT NOT NULL,
            preferred_lang   TEXT NOT NULL DEFAULT 'en',
            created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── alert_history ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER REFERENCES alert_subscriptions(id),
            alert_type      TEXT NOT NULL,
            severity        TEXT NOT NULL DEFAULT 'medium',
            message         TEXT NOT NULL,
            sent_via        TEXT NOT NULL DEFAULT 'sms',
            sent_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── P1 Task 3 indexes on the PII lookup column ────────────────────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alert_subs_phone_hash "
        "ON alert_subscriptions(phone_hash)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_webpush_phone_hash "
        "ON webpush_subscriptions(phone_hash)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_webpush_phone_hash")
    op.execute("DROP INDEX IF EXISTS idx_alert_subs_phone_hash")
    op.execute("DROP TABLE IF EXISTS alert_history")
    op.execute("DROP TABLE IF EXISTS webpush_subscriptions")
    op.execute("DROP TABLE IF EXISTS alert_subscriptions")
