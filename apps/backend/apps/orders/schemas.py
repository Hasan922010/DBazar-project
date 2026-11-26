"""
Pydantic v2 Contracts for Orders & Order Splitting module.
"""
from __future__ import annotations

import uuid
from typing import List
from pydantic import BaseModel, Field


class OrderCartItemInput(BaseModel):
    offer_id: uuid.UUID
    quantity: int = Field(..., ge=1)


class CreateOrderRequest(BaseModel):
    idempotency_key: uuid.UUID
    is_preorder: bool = False
    delivery_address: str = ""
    items: List[OrderCartItemInput] = Field(..., min_length=1)


class SubOrderItemResponse(BaseModel):
    id: uuid.UUID
    variant_id: uuid.UUID
    sku: str
    product_name: str
    mxik_code: str
    barcode: str
    batch_id: str
    quantity: int
    unit_price_tiyin: int
    line_total_tiyin: int


class SubOrderResponse(BaseModel):
    id: uuid.UUID
    seller_org_id: uuid.UUID
    seller_org_name: str
    status: str
    subtotal_amount_tiyin: int
    waybill_qr_token: str
    is_pos_inbounded: bool
    items: List[SubOrderItemResponse]


class OrderResponse(BaseModel):
    id: uuid.UUID
    buyer_org_id: uuid.UUID
    status: str
    is_preorder: bool
    total_amount_tiyin: int
    delivery_address: str
    idempotency_key: uuid.UUID
    sub_orders: List[SubOrderResponse]
