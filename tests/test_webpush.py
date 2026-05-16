import pytest
import logging
from unittest.mock import patch


@pytest.mark.asyncio
async def test_send_web_push_stub_when_no_key(caplog):
    from backend.services.webpush_service import send_web_push
    with patch("backend.services.webpush_service.get_settings") as mock_settings:
        mock_settings.return_value.VAPID_PRIVATE_KEY = ""
        with caplog.at_level(logging.INFO, logger="backend.services.webpush_service"):
            result = await send_web_push(
                "https://fcm.googleapis.com/test", "p256dh-key", "auth-key",
                {"title": "Test", "body": "Hello"}
            )
    assert result is True
    assert "PUSH STUB" in caplog.text
