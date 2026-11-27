"""
Inventory Service Layer:
- Atomic stock receipt and reservation using transaction.atomic() + select_for_update()
- Multi-Tier InventoryLineage tracking
- Strict VMI Telemetry Isolation via PosTelemetryPermission
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import ProductVariant
from apps.iam.models import Organization
from apps.inventory.models import (
    InventoryLineage,
    InventoryStock,
    PosTelemetryPermission,
    Warehouse,
)
from config.api_router import ApiError


@transaction.atomic
def create_warehouse(
    *,
    organization: Organization,
    name: str,
    code: str,
    region: str = "Toshkent",
    address: str = "",
) -> Warehouse:
    if Warehouse.objects.filter(code=code).exists():
        raise ApiError(409, "WAREHOUSE_CODE_EXISTS", f"Ombor kodi '{code}' band.")
    return Warehouse.objects.create(
        organization=organization,
        name=name,
        code=code,
        region=region,
        address=address,
    )


@transaction.atomic
def receive_warehouse_stock(
    *,
    organization: Organization,
    warehouse_id: uuid.UUID,
    variant_id: uuid.UUID,
    batch_id: str,
    qty: int,
    expiry_date: Optional[date] = None,
    min_stock_threshold: int = 10,
) -> InventoryStock:
    if qty <= 0:
        raise ApiError(400, "INVALID_QTY", "Kirim miqdori 0 dan katta bo'lishi shart.")

    warehouse = Warehouse.objects.filter(id=warehouse_id, organization=organization, is_active=True).first()
    if warehouse is None:
        raise ApiError(404, "WAREHOUSE_NOT_FOUND", "Ombor topilmadi yoki sizning tashkilotingizga tegishli emas.")

    variant = ProductVariant.objects.filter(id=variant_id, is_active=True).first()
    if variant is None:
        raise ApiError(404, "VARIANT_NOT_FOUND", "Tovar varianti topilmadi.")

    stock = (
        InventoryStock.objects.select_for_update()
        .filter(warehouse=warehouse, variant=variant, batch_id=batch_id)
        .first()
    )
    if stock is None:
        stock = InventoryStock.objects.create(
            warehouse=warehouse,
            variant=variant,
            batch_id=batch_id,
            available_qty=qty,
            reserved_qty=0,
            min_stock_threshold=min_stock_threshold,
            expiry_date=expiry_date,
        )
    else:
        stock.available_qty += qty
        if expiry_date is not None:
            stock.expiry_date = expiry_date
        stock.save(update_fields=["available_qty", "expiry_date", "updated_at"])

    return stock


@transaction.atomic
def reserve_seller_stock_fefo(
    *,
    seller_org: Organization,
    variant_id: uuid.UUID,
    required_qty: int,
) -> List[tuple[InventoryStock, int]]:
    """
    Atomically locks and reserves `required_qty` across seller's active warehouses
    using `select_for_update()` ordered by `expiry_date` (FEFO: First-Expired, First-Out).
    Returns a list of `(InventoryStock, reserved_from_this_batch)` pairs.
    """
    if required_qty <= 0:
        raise ApiError(400, "INVALID_QTY", "Zahiralash miqdori 0 dan katta bo'lishi shart.")

    stocks = list(
        InventoryStock.objects.select_for_update()
        .select_related("warehouse", "variant")
        .filter(
            warehouse__organization=seller_org,
            warehouse__is_active=True,
            variant_id=variant_id,
            available_qty__gt=0,
        )
        .order_by("expiry_date", "updated_at")
    )

    total_available = sum(s.available_qty for s in stocks)
    if total_available < required_qty:
        raise ApiError(
            409,
            "INSUFFICIENT_STOCK",
            f"Omborda yetarli qoldiq yo'q. Mavjud: {total_available}, so'ralgan: {required_qty}.",
        )

    remaining = required_qty
    allocations: List[tuple[InventoryStock, int]] = []
    for stock in stocks:
        if remaining <= 0:
            break
        take = min(stock.available_qty, remaining)
        stock.available_qty -= take
        stock.reserved_qty += take
        stock.save(update_fields=["available_qty", "reserved_qty", "updated_at"])
        allocations.append((stock, take))
        remaining -= take

    return allocations


@transaction.atomic
def commit_reserved_seller_stock(
    *,
    seller_org: Organization,
    variant_id: uuid.UUID,
    batch_id: str,
    qty: int,
) -> None:
    """
    Releases `reserved_qty` when an order is delivered so reserved stock does not grow forever.
    """
    if batch_id == "PREORDER-BATCH" or qty <= 0:
        return
    stocks = list(
        InventoryStock.objects.select_for_update()
        .filter(
            warehouse__organization=seller_org,
            variant_id=variant_id,
            batch_id=batch_id,
            reserved_qty__gt=0,
        )
        .order_by("updated_at")
    )
    remaining = qty
    for stock in stocks:
        if remaining <= 0:
            break
        deduct = min(stock.reserved_qty, remaining)
        stock.reserved_qty -= deduct
        stock.save(update_fields=["reserved_qty", "updated_at"])
        remaining -= deduct


@transaction.atomic
def release_reserved_seller_stock(
    *,
    seller_org: Organization,
    variant_id: uuid.UUID,
    batch_id: str,
    qty: int,
) -> None:
    """
    Returns `reserved_qty` back to `available_qty` when a PENDING order is cancelled.
    """
    if batch_id == "PREORDER-BATCH" or qty <= 0:
        return
    stocks = list(
        InventoryStock.objects.select_for_update()
        .filter(
            warehouse__organization=seller_org,
            variant_id=variant_id,
            batch_id=batch_id,
            reserved_qty__gt=0,
        )
        .order_by("updated_at")
    )
    remaining = qty
    for stock in stocks:
        if remaining <= 0:
            break
        restore = min(stock.reserved_qty, remaining)
        stock.reserved_qty -= restore
        stock.available_qty += restore
        stock.save(update_fields=["available_qty", "reserved_qty", "updated_at"])
        remaining -= restore


@transaction.atomic
def record_supply_lineage(
    *,
    variant: ProductVariant,
    batch_id: str,
    customer_org: Organization,
    supplied_qty: int,
    manufacturer_org: Optional[Organization] = None,
    intermediary_org: Optional[Organization] = None,
    min_restock_threshold: int = 5,
) -> InventoryLineage:
    lineage = (
        InventoryLineage.objects.select_for_update()
        .filter(customer_org=customer_org, variant=variant, batch_id=batch_id)
        .first()
    )
    mfg = manufacturer_org or variant.product.manufacturer
    if lineage is None:
        lineage = InventoryLineage.objects.create(
            variant=variant,
            batch_id=batch_id,
            manufacturer_org=mfg,
            intermediary_org=intermediary_org,
            customer_org=customer_org,
            supplied_qty=supplied_qty,
            current_pos_qty=supplied_qty,
            sold_pos_qty=0,
            min_restock_threshold=min_restock_threshold,
        )
    else:
        lineage.supplied_qty += supplied_qty
        lineage.current_pos_qty += supplied_qty
        if intermediary_org is not None:
            lineage.intermediary_org = intermediary_org
        lineage.save(update_fields=["supplied_qty", "current_pos_qty", "intermediary_org", "updated_at"])
    return lineage


@transaction.atomic
def set_pos_telemetry_permission(
    *,
    customer_org: Organization,
    viewer_org_id: uuid.UUID,
    is_active: bool = True,
    variant_id: Optional[uuid.UUID] = None,
    batch_id: str = "",
) -> PosTelemetryPermission:
    viewer_org = Organization.objects.filter(id=viewer_org_id).first()
    if viewer_org is None:
        raise ApiError(404, "VIEWER_ORG_NOT_FOUND", "Ruxsat berilayotgan tashkilot topilmadi.")

    perm, created = PosTelemetryPermission.objects.update_or_create(
        customer_org=customer_org,
        viewer_org=viewer_org,
        variant_id=variant_id,
        batch_id=batch_id,
        defaults={
            "is_active": is_active,
            "revoked_at": None if is_active else timezone.now(),
        },
    )
    return perm


def get_isolated_vmi_telemetry(
    *,
    viewer_org: Organization,
    customer_org_id: Optional[uuid.UUID] = None,
) -> List[InventoryLineage]:
    """
    Strictly enforces GEMINI.md rule #5 (VMI Isolation):
    1. Viewer must have an active PosTelemetryPermission granted by the customer_org.
    2. Viewer must be in the supply lineage (intermediary_org == viewer_org or manufacturer_org == viewer_org).
    3. If permission is scoped to a specific variant or batch_id, only matching records are visible.
    """
    active_perms = list(
        PosTelemetryPermission.objects.filter(
            viewer_org=viewer_org,
            is_active=True,
            **({"customer_org_id": customer_org_id} if customer_org_id else {}),
        )
    )
    if not active_perms:
        return []

    perm_query = Q()
    for perm in active_perms:
        sub_q = Q(customer_org_id=perm.customer_org_id)
        if perm.variant_id is not None:
            sub_q &= Q(variant_id=perm.variant_id)
        if perm.batch_id:
            sub_q &= Q(batch_id=perm.batch_id)
        perm_query |= sub_q

    lineage_filter = (Q(intermediary_org=viewer_org) | Q(manufacturer_org=viewer_org)) & perm_query
    return list(
        InventoryLineage.objects.select_related(
            "variant",
            "variant__product",
            "customer_org",
            "intermediary_org",
            "manufacturer_org",
        )
        .filter(lineage_filter)
        .order_by("current_pos_qty")
    )


def get_smart_auto_restock_recommendations(customer_org: Organization) -> List[dict]:
    """
    Phase 4 Smart Auto-Restock:
    Finds store SKUs where `current_pos_qty <= min_restock_threshold` and computes
    recommended restock quantities based on sales velocity (`sold_pos_qty`) and threshold.
    """
    low_lineages = list(
        InventoryLineage.objects.select_related("variant", "variant__product")
        .filter(customer_org=customer_org, current_pos_qty__lte=models.F("min_restock_threshold"))
        .order_by("current_pos_qty")
    )
    results = []
    for ln in low_lineages:
        recommended_qty = max(ln.min_restock_threshold * 4, ln.sold_pos_qty // 2, 20)
        results.append(
            {
                "lineage_id": ln.id,
                "variant_id": ln.variant_id,
                "sku": ln.variant.sku,
                "product_name": f"{ln.variant.product.name} ({ln.variant.name})",
                "current_pos_qty": ln.current_pos_qty,
                "min_restock_threshold": ln.min_restock_threshold,
                "recommended_order_qty": recommended_qty,
                "supplier_org_id": ln.intermediary_org_id or ln.manufacturer_org_id,
            }
        )
    return results


def calculate_ai_regional_demand_forecast(viewer_org: Organization) -> List[dict]:
    """
    Phase 5 AI Demand Forecast:
    Predicts next 30-day regional demand from real-time VMI POS sales (`sold_pos_qty`)
    and supply turnover for SKUs belonging to `viewer_org`.
    """
    lineages = get_isolated_vmi_telemetry(viewer_org=viewer_org)
    grouped: dict[tuple[uuid.UUID, str], dict] = {}
    for ln in lineages:
        region = ln.customer_org.region
        key = (ln.variant_id, region)
        entry = grouped.get(key)
        if entry is None:
            entry = {
                "variant_id": ln.variant_id,
                "sku": ln.variant.sku,
                "product_name": f"{ln.variant.product.name} ({ln.variant.name})",
                "region": region,
                "historical_sold_qty": 0,
            }
            grouped[key] = entry
        entry["historical_sold_qty"] += ln.sold_pos_qty

    forecasts = []
    for item in grouped.values():
        hist = item["historical_sold_qty"]
        # Seasonal growth multiplier (1.25x of observed POS velocity, minimum baseline 50 units)
        forecast_30d = max(int(hist * 1.25), 50)
        forecasts.append(
            {
                **item,
                "forecast_next_30d_qty": forecast_30d,
                "confidence_level": "HIGH" if hist >= 100 else "MEDIUM",
            }
        )
    return forecasts
