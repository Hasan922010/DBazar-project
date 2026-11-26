"""
Pydantic v2 Contracts for Catalog module.
"""
from __future__ import annotations

import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class CreateProductVariantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Tovar nomi")
    brand: str = ""
    description: str = ""
    sku: str = Field(..., min_length=2, max_length=64)
    variant_name: str = Field(..., min_length=2, max_length=255)
    mxik_code: str = Field(..., pattern=r"^\d{17}$", description="17 xonali MXIK kodi")
    barcode: str = Field(..., min_length=4, max_length=32)
    unit_type: Literal["PCS", "BOX", "KG", "LITER"] = "PCS"
    packaging_coefficient: int = Field(default=1, ge=1)
    weight_grams: int = Field(default=0, ge=0)
    category_slug: Optional[str] = None


class ProductVariantResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    brand: str
    sku: str
    variant_name: str
    mxik_code: str
    barcode: str
    unit_type: str
    packaging_coefficient: int
    weight_grams: int


class PriceTierInput(BaseModel):
    min_qty: int = Field(..., ge=1)
    max_qty: Optional[int] = Field(default=None, ge=1)
    unit_price_tiyin: int = Field(..., gt=0, description="1 birlik narxi (tiyinlarda)")


class UpsertOfferRequest(BaseModel):
    variant_id: uuid.UUID
    base_price_tiyin: int = Field(..., gt=0, description="Bazaviy narx (tiyinlarda)")
    min_order_qty: int = Field(default=1, ge=1)
    tiers: List[PriceTierInput] = Field(default_factory=list)


class PriceTierResponse(BaseModel):
    min_qty: int
    max_qty: Optional[int] = None
    unit_price_tiyin: int


class OfferResponse(BaseModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    seller_name: str
    variant: ProductVariantResponse
    base_price_tiyin: int
    min_order_qty: int
    price_tiers: List[PriceTierResponse]


class OfferListResponse(BaseModel):
    items: List[OfferResponse]


class CalculatePriceRequest(BaseModel):
    quantity: int = Field(..., ge=1)


class CalculatePriceResponse(BaseModel):
    offer_id: uuid.UUID
    quantity: int
    unit_price_tiyin: int
    total_price_tiyin: int
