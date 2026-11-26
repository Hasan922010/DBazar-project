"""
Pydantic v2 Contracts for Integrations (Soliq.uz OFD, Didox EHF & DBazar Connect).
"""
from __future__ import annotations

import uuid
from typing import List, Literal
from pydantic import BaseModel, Field


class GenerateDidoxEhfRequest(BaseModel):
    sub_order_id: uuid.UUID
    pkcs7_signature: str = Field(..., min_length=12, description="Sotuvchi E-Imzo PKCS#7 imzosi")


class EhfDocumentResponse(BaseModel):
    id: uuid.UUID
    sub_order_id: uuid.UUID
    didox_doc_id: str
    seller_stir: str
    buyer_stir: str
    total_amount_tiyin: int
    certificate_serial: str
    status: str


class RegisterOfdReceiptRequest(BaseModel):
    store_id: uuid.UUID
    client_sale_id: uuid.UUID
    receipt_seq: int = Field(..., ge=1)
    payment_method: Literal["CASH", "CARD", "MIXED", "NASIYA"] = "CASH"
    total_amount_tiyin: int = Field(..., gt=0)
    mxik_codes: List[str] = Field(..., min_length=1)
    hlc_timestamp: str


class OfdFiscalReceiptResponse(BaseModel):
    id: uuid.UUID
    pos_sale_id: uuid.UUID
    terminal_id: str
    receipt_seq: int
    total_amount_tiyin: int
    fiscal_sign: str
    qr_code_url: str


class DbazarConnectInboundRequest(BaseModel):
    external_system: Literal["1C_ROZNITSA", "BILLZ", "REGOS", "F_APTEKA"]
    terminal_id: str = Field(..., min_length=3, max_length=64)
    waybill_qr_token: str = Field(..., min_length=4, max_length=128)


class DbazarConnectInboundResponse(BaseModel):
    external_system: str
    terminal_id: str
    store_id: uuid.UUID
    sub_order_id: uuid.UUID
    waybill_qr_token: str
    inbounded_items_count: int
    total_waybill_items: int
    is_pos_inbounded: bool
