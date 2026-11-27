"""
Inventory & VMI Telemetry REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

from typing import Optional
import uuid
from django.http import HttpRequest

from apps.iam.models import OrganizationRole, User
from apps.iam.services import require_roles
from apps.inventory.schemas import (
    AutoRestockDraftItemResponse,
    AutoRestockDraftListResponse,
    CreateWarehouseRequest,
    DemandForecastItemResponse,
    DemandForecastListResponse,
    InventoryStockResponse,
    ReceiveStockRequest,
    TelemetryPermissionRequest,
    TelemetryPermissionResponse,
    VmiLineageItemResponse,
    VmiTelemetryDashboardResponse,
    WarehouseResponse,
)
from apps.inventory.services import (
    calculate_ai_regional_demand_forecast,
    create_warehouse,
    get_isolated_vmi_telemetry,
    get_smart_auto_restock_recommendations,
    receive_warehouse_stock,
    set_pos_telemetry_permission,
)
from config.api_router import api_router


@api_router.post(
    "inventory/warehouses",
    response=WarehouseResponse,
    status_code=201,
    tags=["Inventory"],
    summary="Tashkilot uchun yangi ombor yaratish",
    auth=True,
    operation_id="createInventoryWarehouse",
)
def create_warehouse_endpoint(
    request: HttpRequest,
    payload: CreateWarehouseRequest,
) -> WarehouseResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(user, [OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY])
    wh = create_warehouse(
        organization=org,
        name=payload.name,
        code=payload.code,
        region=payload.region,
        address=payload.address,
    )
    return WarehouseResponse(
        id=wh.id,
        organization_id=wh.organization_id,
        name=wh.name,
        code=wh.code,
        region=wh.region,
        address=wh.address,
    )


@api_router.post(
    "inventory/stocks/receive",
    response=InventoryStockResponse,
    status_code=201,
    tags=["Inventory"],
    summary="Omborga partiya (batch_id) va yaroqlilik muddati bilan tovar kirim qilish",
    auth=True,
    operation_id="receiveWarehouseStock",
)
def receive_stock_endpoint(
    request: HttpRequest,
    payload: ReceiveStockRequest,
) -> InventoryStockResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(user, [OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY])
    stock = receive_warehouse_stock(
        organization=org,
        warehouse_id=payload.warehouse_id,
        variant_id=payload.variant_id,
        batch_id=payload.batch_id,
        qty=payload.qty,
        expiry_date=payload.expiry_date,
        min_stock_threshold=payload.min_stock_threshold,
    )
    return InventoryStockResponse(
        id=stock.id,
        warehouse_id=stock.warehouse_id,
        warehouse_code=stock.warehouse.code,
        variant_id=stock.variant_id,
        sku=stock.variant.sku,
        batch_id=stock.batch_id,
        available_qty=stock.available_qty,
        reserved_qty=stock.reserved_qty,
        min_stock_threshold=stock.min_stock_threshold,
        expiry_date=stock.expiry_date,
    )


@api_router.post(
    "inventory/vmi/permissions",
    response=TelemetryPermissionResponse,
    status_code=200,
    tags=["Inventory & VMI"],
    summary="Do'kon tomonidan yetkazib beruvchiga VMI telemetriya ruxsatini berish yoki bekor qilish",
    auth=True,
    operation_id="setPosTelemetryPermission",
)
def set_telemetry_permission_endpoint(
    request: HttpRequest,
    payload: TelemetryPermissionRequest,
) -> TelemetryPermissionResponse:
    user: User = request.user  # type: ignore[assignment]
    customer_org = require_roles(user, [OrganizationRole.CUSTOMER])
    perm = set_pos_telemetry_permission(
        customer_org=customer_org,
        viewer_org_id=payload.viewer_org_id,
        is_active=payload.is_active,
        variant_id=payload.variant_id,
        batch_id=payload.batch_id,
    )
    return TelemetryPermissionResponse(
        id=perm.id,
        customer_org_id=perm.customer_org_id,
        viewer_org_id=perm.viewer_org_id,
        variant_id=perm.variant_id,
        batch_id=perm.batch_id,
        is_active=perm.is_active,
    )


@api_router.get(
    "inventory/vmi/telemetry",
    response=VmiTelemetryDashboardResponse,
    status_code=200,
    tags=["Inventory & VMI"],
    summary="VMI Svetofor Analitika: Do'konlardagi qoldiq, kunlik sotuv va tez tugaydigan tovarlar (Tenant-Isolated)",
    auth=True,
    operation_id="getVmiTelemetryDashboard",
)
def get_vmi_telemetry_endpoint(
    request: HttpRequest,
    customer_org_id: Optional[str] = None,
) -> VmiTelemetryDashboardResponse:
    user: User = request.user  # type: ignore[assignment]
    viewer_org = require_roles(user, [OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY])
    cust_uuid = uuid.UUID(customer_org_id) if customer_org_id else None
    lineages = get_isolated_vmi_telemetry(viewer_org=viewer_org, customer_org_id=cust_uuid)

    items = [
        VmiLineageItemResponse(
            id=ln.id,
            customer_org_id=ln.customer_org_id,
            customer_org_name=ln.customer_org.name,
            variant_id=ln.variant_id,
            sku=ln.variant.sku,
            product_name=f"{ln.variant.product.name} ({ln.variant.name})",
            batch_id=ln.batch_id,
            supplied_qty=ln.supplied_qty,
            current_pos_qty=ln.current_pos_qty,
            sold_pos_qty=ln.sold_pos_qty,
            min_restock_threshold=ln.min_restock_threshold,
            traffic_light_status=ln.traffic_light_status,
        )
        for ln in lineages
    ]
    return VmiTelemetryDashboardResponse(
        total_store_stock_qty=sum(i.current_pos_qty for i in items),
        total_sold_qty=sum(i.sold_pos_qty for i in items),
        low_stock_alert_count=sum(1 for i in items if i.traffic_light_status == "RED"),
        items=items,
    )


@api_router.get(
    "inventory/auto-restock",
    response=AutoRestockDraftListResponse,
    status_code=200,
    tags=["Inventory & VMI"],
    summary="Smart Auto-Restock: Do'kondagi kam qolgan tovarlar uchun 1 tugmada tasdiqlanadigan avto-buyurtma loyihalari",
    auth=True,
    operation_id="getSmartAutoRestockDrafts",
)
def get_auto_restock_endpoint(request: HttpRequest) -> AutoRestockDraftListResponse:
    user: User = request.user  # type: ignore[assignment]
    customer_org = require_roles(user, [OrganizationRole.CUSTOMER])
    recs = get_smart_auto_restock_recommendations(customer_org)
    return AutoRestockDraftListResponse(
        draft_count=len(recs),
        items=[AutoRestockDraftItemResponse(**r) for r in recs],
    )


@api_router.get(
    "inventory/demand-forecast",
    response=DemandForecastListResponse,
    status_code=200,
    tags=["Inventory & VMI"],
    summary="AI Talab Prognozi: POS kassa sotuv tezligi asosida keyingi 30 kunlik hududiy talab prognozi",
    auth=True,
    operation_id="getAiRegionalDemandForecast",
)
def get_demand_forecast_endpoint(request: HttpRequest) -> DemandForecastListResponse:
    user: User = request.user  # type: ignore[assignment]
    viewer_org = require_roles(user, [OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY])
    forecasts = calculate_ai_regional_demand_forecast(viewer_org)
    return DemandForecastListResponse(
        items=[DemandForecastItemResponse(**f) for f in forecasts],
    )
