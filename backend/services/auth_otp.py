"""
OTP storage and verification for phone-based auth.

OTPs are 6-digit random numbers. We never store them in cleartext —
each row carries a per-row random salt and stores ``sha256(otp + salt)``.
A request for the same phone number overwrites any previous unverified
OTP for that number (so resending an OTP invalidates the prior one).

The table lives in the same SQLite file as the alert subsystem
(``settings.SQLITE_PATH``) and is created lazily by :func:`ensure_table`.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time

import aiosqlite

from backend.auth import hash_phone
from backend.config import get_settings

OTP_LENGTH = 6


def _now() -> int:
    return int(time.time())


def _hash_otp(otp: str, salt: str) -> str:
    return hashlib.sha256(f"{otp}:{salt}".encode("utf-8")).hexdigest()


def generate_otp() -> str:
    """Generate a 6-digit numeric OTP using ``secrets`` (CSPRNG)."""
    n = secrets.randbelow(10 ** OTP_LENGTH)
    return f"{n:0{OTP_LENGTH}d}"


async def ensure_table(db: aiosqlite.Connection) -> None:
    """Idempotent schema setup for the OTP table."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_otps (
            phone_hash  TEXT PRIMARY KEY,
            otp_hash    TEXT NOT NULL,
            salt        TEXT NOT NULL,
            expires_at  INTEGER NOT NULL,
            attempts    INTEGER NOT NULL DEFAULT 0,
            created_at  INTEGER NOT NULL
        )
        """
    )
    await db.commit()


async def store_otp(db: aiosqlite.Connection, phone: str, otp: str) -> None:
    """
    Persist an OTP for ``phone``. Overwrites any prior row for the
    same phone, so the latest issued OTP is the only valid one.
    """
    settings = get_settings()
    salt = secrets.token_hex(16)
    await ensure_table(db)
    await db.execute(
        """
        INSERT INTO auth_otps (phone_hash, otp_hash, salt, expires_at, attempts, created_at)
        VALUES (?, ?, ?, ?, 0, ?)
        ON CONFLICT(phone_hash) DO UPDATE SET
            otp_hash   = excluded.otp_hash,
            salt       = excluded.salt,
            expires_at = excluded.expires_at,
            attempts   = 0,
            created_at = excluded.created_at
        """,
        (
            hash_phone(phone),
            _hash_otp(otp, salt),
            salt,
            _now() + settings.OTP_TTL_SECONDS,
            _now(),
        ),
    )
    await db.commit()


async def verify_otp(db: aiosqlite.Connection, phone: str, otp: str) -> bool:
    """
    Check ``otp`` against the stored row for ``phone``.

    On success the row is deleted (single-use). On failure the
    ``attempts`` counter increments; after ``OTP_MAX_ATTEMPTS`` failures
    the row is deleted (lockout — user must request a new OTP).
    """
    settings = get_settings()
    await ensure_table(db)
    ph = hash_phone(phone)
    async with db.execute(
        "SELECT otp_hash, salt, expires_at, attempts FROM auth_otps WHERE phone_hash = ?",
        (ph,),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return False
    otp_hash, salt, expires_at, attempts = row
    if _now() > expires_at:
        await db.execute("DELETE FROM auth_otps WHERE phone_hash = ?", (ph,))
        await db.commit()
        return False
    if attempts >= settings.OTP_MAX_ATTEMPTS:
        await db.execute("DELETE FROM auth_otps WHERE phone_hash = ?", (ph,))
        await db.commit()
        return False
    if _hash_otp(otp, salt) != otp_hash:
        await db.execute(
            "UPDATE auth_otps SET attempts = attempts + 1 WHERE phone_hash = ?",
            (ph,),
        )
        await db.commit()
        return False
    # success — single-use
    await db.execute("DELETE FROM auth_otps WHERE phone_hash = ?", (ph,))
    await db.commit()
    return True
