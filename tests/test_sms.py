import pytest
import logging
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_send_sms_stub_when_no_key(caplog):
    from backend.services.sms import send_sms
    with patch("backend.services.sms.get_settings") as mock_settings:
        mock_settings.return_value.FAST2SMS_API_KEY = ""
        with caplog.at_level(logging.INFO, logger="backend.services.sms"):
            result = await send_sms("+919876543210", "Test alert message")
    assert result is True
    assert "SMS STUB" in caplog.text


def _mock_client(json_body):
    """Build a patched httpx.AsyncClient whose GET returns ``json_body``."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_body)
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=resp)
    return client


@pytest.mark.asyncio
async def test_uses_quick_route_with_message():
    from backend.services import sms
    client = _mock_client({"return": True, "message": ["SMS sent successfully."]})
    with patch("backend.services.sms.get_settings") as mock_settings, \
            patch("backend.services.sms.httpx.AsyncClient", return_value=client):
        mock_settings.return_value.FAST2SMS_API_KEY = "key"
        result = await sms.send_sms("+919876543210", "Your code is 424242")
    assert result is True
    params = client.get.call_args.kwargs["params"]
    assert params["route"] == "q"
    assert params["message"] == "Your code is 424242"
    assert params["numbers"] == "9876543210"  # +91 stripped


@pytest.mark.asyncio
async def test_returns_false_when_fast2sms_rejects(caplog):
    """HTTP 200 + {"return": false} is a FAILURE, not a silent success."""
    from backend.services import sms
    client = _mock_client({"return": False, "message": ["Invalid Authentication"]})
    with patch("backend.services.sms.get_settings") as mock_settings, \
            patch("backend.services.sms.httpx.AsyncClient", return_value=client):
        mock_settings.return_value.FAST2SMS_API_KEY = "bad"
        with caplog.at_level(logging.ERROR, logger="backend.services.sms"):
            result = await sms.send_sms("+919876543210", "x")
    assert result is False
    assert "rejected by Fast2SMS" in caplog.text
