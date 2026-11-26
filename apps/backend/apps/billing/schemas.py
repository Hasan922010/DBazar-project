"""
Pydantic v2 Contracts for Billing, Double-Entry Ledger, Escrow & Data-for-Credit.
"""
from __future__ import annotations

import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class WalletTopupRequest(BaseModel):
    amount_tiyin: int = Field(..., gt=0, description="To'ldirish summasi (tiyinlarda)")
    idempotency_key: uuid.UUID
    provider: Literal["PAYME", "CLICK", "BANK_TRANSFER"] = "PAYME"


class LedgerAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    account_type: str
    currency: str
    balance_tiyin: int
    credit_limit_tiyin: int
    discount_tier_bps: int


class EscrowHoldRequest(BaseModel):
    order_id: uuid.UUID
    idempotency_key: uuid.UUID
    payment_provider: Literal["PAYME", "CLICK", "BANK_TRANSFER", "NASIYA"] = "PAYME"


class EscrowReleaseRequest(BaseModel):
    sub_order_id: uuid.UUID
    idempotency_key: uuid.UUID


class EscrowHoldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    sub_order_id: uuid.UUID
    buyer_org_id: uuid.UUID
    seller_org_id: uuid.UUID
    amount_tiyin: int
    seller_net_tiyin: int
    platform_fee_tiyin: int
    status: str
    payment_provider: str


class EscrowHoldListResponse(BaseModel):
    items: List[EscrowHoldResponse]
