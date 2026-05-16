import aiosqlite
from backend.config import get_settings


async def init_db() -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.SQLITE_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS alert_subscriptions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                phone        TEXT    NOT NULL,
                district     TEXT,
                state        TEXT    NOT NULL,
                crops        TEXT    NOT NULL DEFAULT '[]',
                alert_types  TEXT    NOT NULL DEFAULT '["frost","heavy_rain","pest_risk"]',
                active       INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS webpush_subscriptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                phone      TEXT,
                endpoint   TEXT NOT NULL UNIQUE,
                p256dh     TEXT NOT NULL,
                auth       TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        await db.commit()


async def get_db():
    settings = get_settings()
    db = await aiosqlite.connect(settings.SQLITE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
