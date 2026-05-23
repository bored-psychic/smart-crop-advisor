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
from backend.middleware.rate_limit import limiter, _otp_rate_limit_key
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
@limiter.limit("3/hour", key_func=_otp_rate_limit_key)
async def request_otp(
    request: Request,
    body: RequestOtpBody,
    db: aiosqlite.Connection = Depends(get_db),
):
    phone = _normalise_phone(body.phone)
    # Store the normalised phone on request.state so _otp_rate_limit_key
    # can use it for user-granular bucketing on subsequent slowapi checks.
    request.state.otp_phone = phone
    otp = generate_otp()
    await store_otp(db, phone, otp)
    # Fast2SMS via existing helper. send_sms logs a stub if the key
    # is unset, so this also works in dev without burning SMS credits.
    sent = await send_sms(phone, f"Your KisanOS code is {otp}. Valid for 5 minutes.")
    if not sent:
        raise http_error(502, "otp_send_failed", "Failed to send OTP")
    return RequestOtpResponse(phone=phone)


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp_route(
    body: VerifyOtpBody,
    db: aiosqlite.Connection = Depends(get_db),
):
    phone = _normalise_phone(body.phone)
    ok = await verify_otp(db, phone, body.otp.strip())
    if not ok:
        raise http_error(401, "otp_invalid", "Invalid or expired OTP")
    token, exp = issue_token(phone)
    return VerifyOtpResponse(token=token, exp=exp, phone=phone)


@router.get("/me", response_model=MeResponse)
async def me(user=Depends(require_user)):
    """Returns current token's claims — useful smoke test from the SPA."""
    return MeResponse(phone=user["phone"], sub=user["sub"], exp=user["exp"])
