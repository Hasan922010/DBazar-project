"""
Pydantic v2 Contracts for Logistics (Lite-TMS, GPS Tracking & Proof of Delivery).
"""
from __future__ import annotations

import uuid
from typing import Literal, Optional
from pydantic import BaseModel, Field


class AssignShipmentRequest(BaseModel):
    sub_order_id: uuid.UUID


class UpdateShipmentGpsRequest(BaseModel):
    lat_microdeg: int = Field(..., description="Kenglik mikrogradusda (lat * 1_000_000)")
    lng_microdeg: int = Field(..., description="Uzunlik mikrogradusda (lng * 1_000_000)")
    status: Optional[Literal["PICKED_UP", "IN_TRANSIT"]] = None


class ConfirmPodRequest(BaseModel):
    pod_otp_code: str = Field(..., min_length=6, max_length=6)
    release_idempotency_key: uuid.UUID
    pod_photo_url: str = ""


class ShipmentResponse(BaseModel):
    id: uuid.UUID
    sub_order_id: uuid.UUID
    status: str
    pod_otp_code: str
    current_lat_microdeg: int
    current_lng_microdeg: int
    pod_photo_url: str
