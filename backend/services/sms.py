import logging
import httpx
from backend.config import get_settings
from backend.utils.redaction import mask_phone

logger = logging.getLogger(__name__)

FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"


async def send_sms(phone: str, message: str) -> bool:
    """Send an SMS via Fast2SMS. Returns True only on confirmed delivery.

    Uses the **quick route** (``route=q``) for all messages — it's the route
    available on a plain wallet-funded account. The OTP route (``route=otp``)
    is intentionally *not* used: it requires website verification / DLT that
    this account doesn't have (Fast2SMS rejects it with status 996).

    Fast2SMS returns HTTP 200 *even on failure*, encoding the real outcome in
    a ``{"return": true|false, ...}`` JSON body — so we parse it instead of
    trusting the status code, otherwise a rejected send looks successful.
    """
    settings = get_settings()
    masked_phone = mask_phone(phone)
    if not settings.FAST2SMS_API_KEY:
        logger.info(f"[SMS STUB] To: {masked_phone} | {message}")
        return True

    # Strip country code — Fast2SMS expects a bare 10-digit Indian number.
    number = phone.lstrip("+").removeprefix("91")

    # Fast2SMS authenticates the key as a *query parameter*, not an HTTP header.
    # The header form (authorization: <key>) is rejected with status 412
    # "Invalid Authentication" for our dev-API key, even though the key is valid
    # — verified against /dev/wallet (header → 412, query param → return:true).
    params = {
        "authorization": settings.FAST2SMS_API_KEY,
        "route": "q",
        "message": message,
        "numbers": number,
        "flash": 0,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(FAST2SMS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"SMS request failed to {masked_phone}: {e}")
            return False

    # Business-level result lives in the body, not the HTTP status.
    if data.get("return") is True:
        logger.info(f"SMS delivered to {masked_phone}: {data.get('message')}")
        return True
    logger.error(f"SMS rejected by Fast2SMS for {masked_phone}: {data}")
    return False
