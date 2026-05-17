"""Tests that init_db creates / adds preferred_lang on both subscription tables."""
import aiosqlite
import pytest

from backend.services.db import init_db
from backend.config import get_settings


@pytest.mark.asyncio
async def test_alert_subscriptions_has_preferred_lang(tmp_path, monkeypatch):
    db_path = tmp_path / "kisanos_test.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    await init_db()

    async with aiosqlite.connect(str(db_path)) as db:
        rows = await (await db.execute("PRAGMA table_info(alert_subscriptions)")).fetchall()
        cols = {r[1]: r for r in rows}
        assert "preferred_lang" in cols
        assert cols["preferred_lang"][4] == "'en'"


@pytest.mark.asyncio
async def test_webpush_subscriptions_has_preferred_lang(tmp_path, monkeypatch):
    db_path = tmp_path / "kisanos_test2.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    await init_db()

    async with aiosqlite.connect(str(db_path)) as db:
        rows = await (await db.execute("PRAGMA table_info(webpush_subscriptions)")).fetchall()
        cols = {r[1] for r in rows}
        assert "preferred_lang" in cols


@pytest.mark.asyncio
async def test_init_db_is_idempotent_on_existing_db(tmp_path, monkeypatch):
    db_path = tmp_path / "kisanos_test3.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    await init_db()
    await init_db()

    async with aiosqlite.connect(str(db_path)) as db:
        rows = await (await db.execute("PRAGMA table_info(alert_subscriptions)")).fetchall()
        cols = {r[1] for r in rows}
        assert "preferred_lang" in cols
