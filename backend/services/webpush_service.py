import json
import logging
from pywebpush import webpush, WebPushException
from backend.config import get_settings

logger = logging.getLogger(__name__)


async def send_web_push(endpoint: str, p256dh: str, auth: str, payload: dict) -> bool:
    settings = get_settings()
    if not settings.VAPID_PRIVATE_KEY:
        logger.info(f"[PUSH STUB] To: {endpoint[:60]}… | {payload}")
        return True

    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_EMAIL},
        )
        return True
    except WebPushException as e:
        logger.error(f"Web push failed to {endpoint[:60]}: {e}")
        return False
