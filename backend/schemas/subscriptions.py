from __future__ import annotations
from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from core.disease_db import DISEASE_DB

# Authoritative crop allowlist derived from the disease DB (single source of truth).
_VALID_CROPS: frozenset[str] = frozenset(DISEASE_DB.keys())


class SubscribeRequest(BaseModel):
    phone: Annotated[str, Field(pattern=r"^\+?[1-9]\d{7,14}$")]
    district: Optional[str] = None
    state: str
    crops: Annotated[list[str], Field(max_length=20)]
    alert_types: list[Literal["frost", "heavy_rain", "pest_risk"]] = [
        "frost", "heavy_rain", "pest_risk"
    ]

    @field_validator("crops")
    @classmethod
    def crops_must_be_known(cls, v: list[str]) -> list[str]:
        unknown = [c for c in v if c not in _VALID_CROPS]
        if unknown:
            raise ValueError(
                f"Unknown crop(s): {unknown}. Valid crops: {sorted(_VALID_CROPS)}"
            )
        return v


class SubscribeResponse(BaseModel):
    id: int
    phone: str
    state: str
    crops: list[str]
    alert_types: list[str]
    message: str = "Subscribed successfully"


class PushSubscribeRequest(BaseModel):
    phone: Optional[str] = None
    endpoint: str
    p256dh: str
    auth: str


class VapidKeyResponse(BaseModel):
    public_key: str


class AlertHistoryItem(BaseModel):
    id: int
    alert_type: str
    severity: str
    message: str
    sent_at: str
