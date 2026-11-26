"""
POS Sync REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

from django.http import HttpRequest

from apps.iam.models import OrganizationRole, User
from apps.iam.services import require_roles
from apps.pos_sync.schemas import (
    CreatePosStoreRequest,
    OneClickWaybillInboundRequest,
    OneClickWaybillInboundResponse,
    PosDeltaSyncBatchRequest,
    PosDeltaSyncBatchResponse,
    PosStoreResponse,
)
from apps.pos_sync.services import (
    create_pos_store,
    execute_one_click_waybill_inbound,
    ingest_pos_delta_events,
)
from config.api_router import api_router


@api_router.post(
    "pos-sync/stores",
    response=PosStoreResponse,
    status_code=201,
    tags=["POS Sync"],
    summary="Yangi POS kassa nuqtasini ro'yxatdan o'tkazish",
    auth=True,
    operation_id="createPosStore",
)
def create_pos_store_endpoint(
    request: HttpRequest,
    payload: CreatePosStoreRequest,
) -> PosStoreResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(user, [OrganizationRole.CUSTOMER])
    store = create_pos_store(
        organization=org,
        name=payload.name,
        terminal_id=payload.terminal_id,
        address=payload.address,
    )
    return PosStoreResponse(
        id=store.id,
        organization_id=store.organization_id,
        name=store.name,
        terminal_id=store.terminal_id,
        address=store.address,
        last_hlc_timestamp=store.last_hlc_timestamp,
    )


@api_router.post(
    "pos-sync/delta",
    response=PosDeltaSyncBatchResponse,
    status_code=200,
    tags=["POS Sync"],
    summary="Oflayn POS kassadan append-only HLC Delta-paketni ziddiyatsiz sinxronlash",
    auth=True,
    operation_id="syncPosDeltaBatch",
)
def sync_pos_delta_endpoint(
    request: HttpRequest,
    payload: PosDeltaSyncBatchRequest,
) -> PosDeltaSyncBatchResponse:
    user: User = request.user  # type: ignore[assignment]
    customer_org = require_roles(user, [OrganizationRole.CUSTOMER])
    result = ingest_pos_delta_events(
        customer_org=customer_org,
        store_id=payload.store_id,
        events=[e.model_dump() for e in payload.events],
    )
    return PosDeltaSyncBatchResponse(**result)


@api_router.post(
    "pos-sync/one-click-inbound",
    response=OneClickWaybillInboundResponse,
    status_code=200,
    tags=["POS Sync"],
    summary="1-Click Avto-Kirim: Yuk xati QR-kodini skanerlab barcha tovar va MXIK larni 1 soniyada kirim qilish",
    auth=True,
    operation_id="oneClickWaybillInbound",
)
def one_click_inbound_endpoint(
    request: HttpRequest,
    payload: OneClickWaybillInboundRequest,
) -> OneClickWaybillInboundResponse:
    user: User = request.user  # type: ignore[assignment]
    customer_org = require_roles(user, [OrganizationRole.CUSTOMER])
    result = execute_one_click_waybill_inbound(
        customer_org=customer_org,
        store_id=payload.store_id,
        waybill_qr_token=payload.waybill_qr_token,
    )
    return OneClickWaybillInboundResponse(**result)
