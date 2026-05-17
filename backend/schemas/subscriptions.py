from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


class SubscribeRequest(BaseModel):
    phone: str
    district: Optional[str] = None
    state: str
    crops: list[str]
    alert_types: list[Literal["frost", "heavy_rain", "pest_risk"]] = [
        "frost", "heavy_rain", "pest_risk"
    ]


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
