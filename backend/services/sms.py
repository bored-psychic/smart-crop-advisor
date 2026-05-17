import logging
import httpx
from backend.config import get_settings

logger = logging.getLogger(__name__)


async def send_sms(phone: str, message: str) -> bool:
    settings = get_settings()
    if not settings.FAST2SMS_API_KEY:
        logger.info(f"[SMS STUB] To: {phone} | {message}")
        return True

    # Strip country code — Fast2SMS expects 10-digit Indian number
    number = phone.lstrip("+").removeprefix("91")

    url = "https://www.fast2sms.com/dev/bulkV2"
    params = {
        "authorization": settings.FAST2SMS_API_KEY,
        "variables_values": message,
        "route": "q",          # quick route; switch to 'dlt' once DLT template approved
        "numbers": number,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            logger.info(f"SMS sent to {phone}: {resp.text}")
            return True
        except Exception as e:
            logger.error(f"SMS failed to {phone}: {e}")
            return False
