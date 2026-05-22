import logging
import httpx
from backend.config import get_settings

logger = logging.getLogger(__name__)


async def send_sms(phone: str, message: str) -> bool:
    settings = get_settings()
    masked_phone = phone[:3] + "***" + phone[-2:]
    if not settings.FAST2SMS_API_KEY:
        logger.info(f"[SMS STUB] To: {masked_phone} | {message}")
        return True

    # Strip country code — Fast2SMS expects 10-digit Indian number
    number = phone.lstrip("+").removeprefix("91")

    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        "authorization": settings.FAST2SMS_API_KEY,
    }
    params = {
        "message": message,
        "route": "q",          # quick route; switch to 'dlt' once DLT template approved
        "numbers": number,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            logger.info(f"SMS sent to {masked_phone}: {resp.status_code}")
            return True
        except Exception as e:
            logger.error(f"SMS failed to {masked_phone}: {e}")
            return False
