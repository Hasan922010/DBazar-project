"""
Pydantic v2 Contracts for Offline-First POS Delta-Sync & 1-Click Auto-Inbound.
"""
from __future__ import annotations

import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class CreatePosStoreRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    terminal_id: str = Field(..., min_length=3, max_length=64)
    address: str = ""


class PosStoreResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    terminal_id: str
    address: str
    last_hlc_timestamp: str


class PosDeltaEventInput(BaseModel):
    client_event_id: uuid.UUID
    variant_id: uuid.UUID
    batch_id: str = "DEFAULT-BATCH"
    event_type: Literal["INBOUND", "SALE", "RETURN", "WRITE_OFF"]
    quantity: int = Field(..., gt=0)
    unit_price_tiyin: int = Field(default=0, ge=0)
    hlc_timestamp: str = Field(..., description="Format: <wall_ms>:<counter>:<node_id>")
    waybill_qr_token: Optional[str] = ""


class PosDeltaSyncBatchRequest(BaseModel):
    store_id: uuid.UUID
    events: List[PosDeltaEventInput] = Field(..., min_length=1)


class PosDeltaSyncBatchResponse(BaseModel):
    store_id: uuid.UUID
    applied_events: int
    skipped_duplicates: int
    conflicts: int
    last_hlc_timestamp: str


class OneClickWaybillInboundRequest(BaseModel):
    store_id: uuid.UUID
    waybill_qr_token: str = Field(..., min_length=4, max_length=128)


class OneClickWaybillInboundResponse(BaseModel):
    store_id: uuid.UUID
    sub_order_id: uuid.UUID
    waybill_qr_token: str
    inbounded_items_count: int
    total_waybill_items: int
    is_pos_inbounded: bool
