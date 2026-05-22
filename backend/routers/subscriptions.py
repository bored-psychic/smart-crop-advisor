import json
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.schemas.subscriptions import (
    SubscribeRequest, SubscribeResponse,
    PushSubscribeRequest, VapidKeyResponse,
)
from backend.auth import require_api_key, require_user
from backend.config import get_settings
from backend.services.db import get_db
from backend.services.alerts import check_and_send_alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    req: SubscribeRequest,
    user=Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute(
        """INSERT INTO alert_subscriptions
           (phone, district, state, crops, alert_types)
           VALUES (?, ?, ?, ?, ?)""",
        (req.phone, req.district, req.state,
         json.dumps(req.crops), json.dumps(req.alert_types)),
    ) as cursor:
        sub_id = cursor.lastrowid
    await db.commit()
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
    phone: str,
    user=Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    # NOTE: Task 6 will replace the `phone` query param with the JWT
    # subject. For T3 we only swap the auth dependency.
    async with db.execute(
        """SELECT ah.id, ah.alert_type, ah.severity, ah.message, ah.sent_at
           FROM alert_history ah
           JOIN alert_subscriptions s ON s.id = ah.subscription_id
           WHERE s.phone = ?
           ORDER BY ah.sent_at DESC LIMIT 50""",
        (phone,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("/push-subscribe")
async def push_subscribe(
    req: PushSubscribeRequest,
    user=Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    await db.execute(
        """INSERT INTO webpush_subscriptions (phone, endpoint, p256dh, auth)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(endpoint) DO UPDATE SET phone=excluded.phone""",
        (req.phone, req.endpoint, req.p256dh, req.auth),
    )
    await db.commit()
    return {"message": "Push subscription saved"}


@router.get("/vapid-public-key", response_model=VapidKeyResponse)
async def vapid_key():
    settings = get_settings()
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(503, "VAPID keys not configured")
    return VapidKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/trigger-check")
async def trigger_check(_=Depends(require_api_key)):
    """Manual trigger for testing — runs the full alert pipeline immediately.

    Stays on the service-to-service ``require_api_key`` guard: this route
    is for cron/admin use, not the browser.
    """
    await check_and_send_alerts()
    return {"message": "Alert check complete"}
