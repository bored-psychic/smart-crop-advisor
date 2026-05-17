import pytest
import logging
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_send_sms_stub_when_no_key(caplog):
    from backend.services.sms import send_sms
    with patch("backend.services.sms.get_settings") as mock_settings:
        mock_settings.return_value.FAST2SMS_API_KEY = ""
        with caplog.at_level(logging.INFO, logger="backend.services.sms"):
            result = await send_sms("+919876543210", "Test alert message")
    assert result is True
    assert "SMS STUB" in caplog.text
