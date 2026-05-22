import aiosqlite
from backend.config import get_settings


async def init_db() -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.SQLITE_PATH) as db:
        # NOTE: `phone` is retained as a nullable column for backward
        # compatibility with already-migrated rows. New writes leave it
        # NULL — the lookup key is `phone_hash` (peppered SHA-256) and
        # the readable form is `phone_ciphertext` (Fernet). See
        # P1 Task 3: "Encrypt PII at rest".
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS alert_subscriptions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                phone             TEXT,
                phone_hash        TEXT,
                phone_ciphertext  TEXT,
                district          TEXT,
                state             TEXT    NOT NULL,
                crops             TEXT    NOT NULL DEFAULT '[]',
                alert_types       TEXT    NOT NULL DEFAULT '["frost","heavy_rain","pest_risk"]',
                active            INTEGER NOT NULL DEFAULT 1,
                preferred_lang    TEXT    NOT NULL DEFAULT 'en',
                created_at        TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS webpush_subscriptions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                phone             TEXT,
                phone_hash        TEXT,
                phone_ciphertext  TEXT,
                endpoint          TEXT NOT NULL UNIQUE,
                p256dh            TEXT NOT NULL,
                auth              TEXT NOT NULL,
                preferred_lang    TEXT    NOT NULL DEFAULT 'en',
                created_at        TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS alert_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER REFERENCES alert_subscriptions(id),
                alert_type      TEXT NOT NULL,
                severity        TEXT NOT NULL DEFAULT 'medium',
                message         TEXT NOT NULL,
                sent_via        TEXT NOT NULL DEFAULT 'sms',
                sent_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        for table in ("alert_subscriptions", "webpush_subscriptions"):
            cursor = await db.execute(f"PRAGMA table_info({table})")
            cols = {row[1] for row in await cursor.fetchall()}
            if "preferred_lang" not in cols:
                await db.execute(
                    f"ALTER TABLE {table} ADD COLUMN preferred_lang TEXT NOT NULL DEFAULT 'en'"
                )
            # PII-at-rest migration (idempotent ALTER TABLE for existing dbs).
            if "phone_hash" not in cols:
                await db.execute(
                    f"ALTER TABLE {table} ADD COLUMN phone_hash TEXT"
                )
            if "phone_ciphertext" not in cols:
                await db.execute(
                    f"ALTER TABLE {table} ADD COLUMN phone_ciphertext TEXT"
                )

        # Index the lookup column — equality checks against phone_hash
        # are the new hot path (subscriptions.history, alerts cross-table
        # joins after migrate_pii.py is run).
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_subs_phone_hash "
            "ON alert_subscriptions(phone_hash)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_webpush_phone_hash "
            "ON webpush_subscriptions(phone_hash)"
        )

        await db.commit()


async def get_db():
    settings = get_settings()
    db = await aiosqlite.connect(settings.SQLITE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
