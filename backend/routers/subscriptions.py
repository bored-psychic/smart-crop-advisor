import hashlib
import json
import aiosqlite
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, Request

from backend.schemas.errors import http_error
from backend.schemas.subscriptions import (
    SubscribeRequest, SubscribeResponse,
    PushSubscribeRequest, VapidKeyResponse,
)
from backend.auth import require_api_key, require_user
from backend.config import get_settings
from backend.middleware.rate_limit import limiter
from backend.services.db import get_db
from backend.services.alerts import check_and_send_alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ─── PII helpers (P1 Task 3) ──────────────────────────────────────────
#
# `phone_hash` is a peppered SHA-256 of the E.164 string and serves as the
# equality lookup column (history JOIN, webpush phone_hash = ?). It is
# distinct from auth.hash_phone() — that one is unpeppered and used as
# the JWT `sub` claim, which must be derivable client-side. The DB-side
# hash uses APP_PEPPER so an attacker with a dump cannot brute-force the
# full E.164 keyspace in seconds.
#
# `phone_ciphertext` is Fernet(AES-128-CBC + HMAC) so the original phone
# can be returned to the rightful owner when they hit /alerts/* with a
# valid JWT for that phone. The plaintext `phone` column is left NULL on
# new writes — old rows are backfilled by scripts/migrate_pii.py.

def _peppered_phone_hash(phone: str) -> str:
    settings = get_settings()
    return hashlib.sha256(
        (phone + settings.APP_PEPPER).encode("utf-8")
    ).hexdigest()


def _encrypt_phone(phone: str) -> str:
    settings = get_settings()
    return Fernet(settings.FERNET_KEY.encode()).encrypt(
        phone.encode("utf-8")
    ).decode("utf-8")


def _decrypt_phone(ct: str | None) -> str | None:
    if not ct:
        return None
    settings = get_settings()
    try:
        return Fernet(settings.FERNET_KEY.encode()).decrypt(
            ct.encode("utf-8")
        ).decode("utf-8")
    except InvalidToken:
        return None


@router.post("/subscribe", response_model=SubscribeResponse)
@limiter.limit("5/hour")
async def subscribe(
    request: Request,
    req: SubscribeRequest,
    user=Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    phone_hash = _peppered_phone_hash(req.phone)
    phone_ct = _encrypt_phone(req.phone)
    async with db.execute(
        """INSERT INTO alert_subscriptions
           (phone, phone_hash, phone_ciphertext, district, state, crops, alert_types)
           VALUES (NULL, ?, ?, ?, ?, ?, ?)""",
        (phone_hash, phone_ct, req.district, req.state,
         json.dumps(req.crops), json.dumps(req.alert_types)),
    ) as cursor:
        sub_id = cursor.lastrowid
    await db.commit()
    # Return the original phone in the response (decrypt-on-read pattern,
    # though here we trivially echo the value we just received).
    return SubscribeResponse(
        id=sub_id, phone=req.phone, state=req.state,
        crops=req.crops, alert_types=req.alert_types,
    )


@router.delete("/unsubscribe/{sub_id}")
async def unsubscribe(
    sub_id: int,
    user=Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    await db.execute(
        "UPDATE alert_subscriptions SET active = 0 WHERE id = ?", (sub_id,)
    )
    await db.commit()
    return {"message": "Unsubscribed successfully"}


@router.get("/history")
async def history(
    request: Request,
    user=Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    # Task 6: phone is derived from the verified JWT — never from the query
    # string.  A caller who presents a token for phone A cannot read history
    # belonging to phone B.
    #
    # 403-vs-empty-result: we return an empty list rather than 403 when a
    # phone simply has no history.  Returning 403 would distinguish "phone
    # exists in our system" from "phone unknown", creating an enumeration
    # oracle.  An empty list is indistinguishable from "no alerts sent yet"
    # and leaks nothing about whether other phones are subscribed.
    #
    # P1 Task 3: lookup is by peppered phone_hash now that the plaintext
    # `phone` column is NULL on new rows. Old rows still match via the
    # OR clause until the migration script has been run + verified.
    phone: str = request.state.user["phone"]
    phone_hash = _peppered_phone_hash(phone)
    async with db.execute(
        """SELECT ah.id, ah.alert_type, ah.severity, ah.message, ah.sent_at
           FROM alert_history ah
           JOIN alert_subscriptions s ON s.id = ah.subscription_id
           WHERE s.phone_hash = ? OR s.phone = ?
           ORDER BY ah.sent_at DESC LIMIT 50""",
        (phone_hash, phone),
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("/push-subscribe")
async def push_subscribe(
    req: PushSubscribeRequest,
    user=Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    phone_hash = _peppered_phone_hash(req.phone) if req.phone else None
    phone_ct = _encrypt_phone(req.phone) if req.phone else None
    await db.execute(
        """INSERT INTO webpush_subscriptions
           (phone, phone_hash, phone_ciphertext, endpoint, p256dh, auth)
           VALUES (NULL, ?, ?, ?, ?, ?)
           ON CONFLICT(endpoint) DO UPDATE SET
              phone=NULL,
              phone_hash=excluded.phone_hash,
              phone_ciphertext=excluded.phone_ciphertext""",
        (phone_hash, phone_ct, req.endpoint, req.p256dh, req.auth),
    )
    await db.commit()
    return {"message": "Push subscription saved"}


@router.get("/vapid-public-key", response_model=VapidKeyResponse)
async def vapid_key(user=Depends(require_user)):
    settings = get_settings()
    if not settings.VAPID_PUBLIC_KEY:
        raise http_error(503, "vapid_not_configured", "VAPID keys not configured")
    return VapidKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/trigger-check")
async def trigger_check(_=Depends(require_api_key)):
    """Manual trigger for testing — runs the full alert pipeline immediately.

    Stays on the service-to-service ``require_api_key`` guard: this route
    is for cron/admin use, not the browser.
    """
    await check_and_send_alerts()
    return {"message": "Alert check complete"}
