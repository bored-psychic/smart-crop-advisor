"""add hot-column indexes for phone_hash lookup paths (P2 Task 2)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-22

Adds the canonical P2-spec index names on the alert_subscriptions and
webpush_subscriptions tables for the phone_hash column.  These complement
the idx_alert_subs_phone_hash / idx_webpush_phone_hash indexes from 0001
and provide the exact names documented in P2-medium.md Task 2.

Using IF NOT EXISTS so the migration is safely re-entrant on databases where
any of these were created manually.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Canonical index names from P2-medium.md spec.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_alert_subscriptions_phone "
        "ON alert_subscriptions(phone_hash)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_webpush_subscriptions_phone "
        "ON webpush_subscriptions(phone_hash)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_webpush_subscriptions_phone")
    op.execute("DROP INDEX IF EXISTS idx_alert_subscriptions_phone")
