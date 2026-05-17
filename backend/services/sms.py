import logging
import httpx
from backend.config import get_settings

logger = logging.getLogger(__name__)


async def send_sms(phone: str, message: str) -> bool:
    settings = get_settings()
    if not settings.MSG91_API_KEY:
        logger.info(f"[SMS STUB] To: {phone} | {message}")
        return True

    url = "https://api.msg91.com/api/sendhttp.php"
    params = {
        "authkey": settings.MSG91_API_KEY,
        "mobiles": phone.lstrip("+"),
        "message": message,
        "sender": settings.MSG91_SENDER_ID,
        "route": "4",
        "country": "91",
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
