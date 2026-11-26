"""
Pydantic v2 Contracts for Inventory & VMI Telemetry module.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class CreateWarehouseRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=64)
    region: str = "Toshkent"
    address: str = ""


class WarehouseResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    code: str
    region: str
    address: str


class ReceiveStockRequest(BaseModel):
    warehouse_id: uuid.UUID
    variant_id: uuid.UUID
    batch_id: str = Field(..., min_length=1, max_length=64)
    qty: int = Field(..., gt=0)
    expiry_date: Optional[date] = None
    min_stock_threshold: int = Field(default=10, ge=0)


class InventoryStockResponse(BaseModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    warehouse_code: str
    variant_id: uuid.UUID
    sku: str
    batch_id: str
    available_qty: int
    reserved_qty: int
    min_stock_threshold: int
    expiry_date: Optional[date] = None


class TelemetryPermissionRequest(BaseModel):
    viewer_org_id: uuid.UUID
    is_active: bool = True
    variant_id: Optional[uuid.UUID] = None
    batch_id: str = ""


class TelemetryPermissionResponse(BaseModel):
    id: uuid.UUID
    customer_org_id: uuid.UUID
    viewer_org_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    batch_id: str
    is_active: bool


class VmiLineageItemResponse(BaseModel):
    id: uuid.UUID
    customer_org_id: uuid.UUID
    customer_org_name: str
    variant_id: uuid.UUID
    sku: str
    product_name: str
    batch_id: str
    supplied_qty: int
    current_pos_qty: int
    sold_pos_qty: int
    min_restock_threshold: int
    traffic_light_status: str


class VmiTelemetryDashboardResponse(BaseModel):
    total_store_stock_qty: int
    total_sold_qty: int
    low_stock_alert_count: int
    items: List[VmiLineageItemResponse]
