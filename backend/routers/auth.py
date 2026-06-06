"""
Phone + OTP authentication endpoints.

Two-step flow:

1. ``POST /auth/request-otp { phone }`` — sends a 6-digit OTP to the
   phone via Fast2SMS (or logs a stub if ``FAST2SMS_API_KEY`` is unset).
2. ``POST /auth/verify-otp { phone, otp }`` — on match, returns a signed
   JWT for use as ``Authorization: Bearer <token>``.

Phone numbers are normalised to a loose E.164 (``+`` + digits only)
before hashing/sending so that ``9876543210`` and ``+91 98765 43210``
hash to the same identifier.
"""

from __future__ import annotations

import re

import aiosqlite
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.auth import issue_token, require_user
from backend.schemas.errors import http_error
from backend.middleware.rate_limit import limiter, _otp_rate_limit_key, _otp_phone_dep
from backend.services.auth_otp import (
    generate_otp,
    store_otp,
    verify_otp,
)
from backend.services.db import get_db
from backend.services.sms import send_sms

router = APIRouter(prefix="/api/auth", tags=["auth"])


_DIGITS = re.compile(r"\D+")


def _normalise_phone(raw: str) -> str:
    """
    Collapse user-supplied phone strings to ``+<digits>`` form.

    Accepts ``98765 43210``, ``+91 98765-43210``, ``919876543210``, etc.
    Defaults missing country codes to ``+91`` (India — the only market
    Fast2SMS supports). Rejects anything shorter than 10 digits.
    """
    digits = _DIGITS.sub("", raw or "")
    if not digits:
        raise http_error(400, "phone_required", "Phone number required")
    if len(digits) == 10:
        digits = "91" + digits
    if len(digits) < 10:
        raise http_error(400, "phone_too_short", "Phone number too short")
    return "+" + digits


class RequestOtpBody(BaseModel):
    phone: str = Field(..., min_length=4, max_length=20)


class RequestOtpResponse(BaseModel):
    ok: bool = True
    # Echo the normalised number so the client can keep state in sync.
    phone: str
    # Demo-mode only: when FAST2SMS_API_KEY is unset, we cannot deliver
    # the code by SMS, so we return it to the client for on-screen display.
    # Never populated in production (where the key is set).
    demo_otp: str | None = None


class VerifyOtpBody(BaseModel):
    phone: str
    otp: str = Field(..., min_length=4, max_length=8)


class VerifyOtpResponse(BaseModel):
    token: str
    exp: int
    phone: str


class MeResponse(BaseModel):
    phone: str
    sub: str
    exp: int


@router.post("/request-otp", response_model=RequestOtpResponse)
@limiter.limit("5/hour", key_func=_otp_rate_limit_key)
async def request_otp(
    request: Request,
    body: RequestOtpBody,
    db: aiosqlite.Connection = Depends(get_db),
    _phone_for_limit: None = Depends(_otp_phone_dep),
):
    phone = _normalise_phone(body.phone)
    # Store the normalised phone on request.state so _otp_rate_limit_key
    # can use it for user-granular bucketing on subsequent slowapi checks.
    request.state.otp_phone = phone
    otp = generate_otp()
    await store_otp(db, phone, otp)
    # Fast2SMS via existing helper. send_sms logs a stub if the key
    # is unset, so this also works in dev without burning SMS credits.
    from backend.config import get_settings
    settings = get_settings()
    sms_enabled = bool(settings.FAST2SMS_API_KEY)

    # Dedicated demo number: skip the ₹5 quick-route SMS and surface the OTP
    # on screen instead. Only this one configured number is treated this way.
    demo_target = None
    if settings.DEMO_PHONE:
        try:
            demo_target = _normalise_phone(settings.DEMO_PHONE)
        except Exception:
            demo_target = None
    is_demo_number = demo_target is not None and phone == demo_target

    if is_demo_number:
        sent = True  # no SMS sent — no charge
    else:
        sent = await send_sms(phone, f"Your KisanOS code is {otp}. Valid for 5 minutes.")
        if not sent and sms_enabled:
            raise http_error(502, "otp_send_failed", "Failed to send OTP")
    # Surface the OTP back to the SPA when (a) it's the dedicated demo number, or
    # (b) the legacy dev fallback (non-production AND no SMS configured). For
    # every other production number this is None — real codes are never leaked.
    demo_mode = is_demo_number or (
        (not settings.is_production) and (not sms_enabled)
    )
    return RequestOtpResponse(
        phone=phone,
        demo_otp=otp if demo_mode else None,
    )


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp_route(
    body: VerifyOtpBody,
    db: aiosqlite.Connection = Depends(get_db),
):
    phone = _normalise_phone(body.phone)
    supplied_otp = body.otp.strip()
    # Demo mode: accept the universal magic code 123456 so a presenter can sign
    # in without an SMS round-trip. SECURITY: gated on non-production AND no SMS,
    # so production never honours the magic code regardless of SMS config.
    from backend.config import get_settings
    settings = get_settings()
    magic_ok = (
        (not settings.is_production)
        and (not settings.FAST2SMS_API_KEY)
        and supplied_otp == "123456"
    )
    ok = magic_ok or await verify_otp(db, phone, supplied_otp)
    if not ok:
        raise http_error(401, "otp_invalid", "Invalid or expired OTP")
    token, exp = issue_token(phone)
    return VerifyOtpResponse(token=token, exp=exp, phone=phone)


@router.get("/me", response_model=MeResponse)
async def me(user=Depends(require_user)):
    """Returns current token's claims — useful smoke test from the SPA."""
    return MeResponse(phone=user["phone"], sub=user["sub"], exp=user["exp"])
