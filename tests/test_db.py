import os, pytest, tempfile

# Create a temp file DB so both init_db() and the verification share the same path.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SQLITE_PATH"] = _tmp.name

@pytest.mark.asyncio
async def test_init_db_creates_tables():
    import aiosqlite
    from backend.config import get_settings

    # Clear the lru_cache so the env var set above is picked up.
    get_settings.cache_clear()

    from backend.services.db import init_db
    settings = get_settings()
    await init_db()
    async with aiosqlite.connect(settings.SQLITE_PATH) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cur:
            tables = {row[0] async for row in cur}
    assert "alert_subscriptions" in tables
    assert "webpush_subscriptions" in tables
    assert "alert_history" in tables
