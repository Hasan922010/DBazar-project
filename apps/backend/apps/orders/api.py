"""
Orders REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

from django.http import HttpRequest

from apps.iam.models import OrganizationRole, User
from apps.iam.services import require_roles
from apps.orders.models import Order, SubOrder
from apps.orders.schemas import (
    CreateOrderRequest,
    OrderResponse,
    SubOrderItemResponse,
    SubOrderResponse,
)
from apps.orders.services import create_b2b_order_with_splitting, get_waybill_by_qr_token
from config.api_router import api_router


def serialize_sub_order(sub: SubOrder) -> SubOrderResponse:
    return SubOrderResponse(
        id=sub.id,
        seller_org_id=sub.seller_org_id,
        seller_org_name=sub.seller_org.name,
        status=sub.status,
        subtotal_amount_tiyin=sub.subtotal_amount_tiyin,
        waybill_qr_token=sub.waybill_qr_token,
        is_pos_inbounded=sub.is_pos_inbounded,
        items=[
            SubOrderItemResponse(
                id=item.id,
                variant_id=item.variant_id,
                sku=item.variant.sku,
                product_name=f"{item.variant.product.name} ({item.variant.name})",
                mxik_code=item.variant.mxik_code,
                barcode=item.variant.barcode,
                batch_id=item.batch_id,
                quantity=item.quantity,
                unit_price_tiyin=item.unit_price_tiyin,
                line_total_tiyin=item.line_total_tiyin,
            )
            for item in sub.items.all()
        ],
    )


def serialize_order(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        buyer_org_id=order.buyer_org_id,
        status=order.status,
        is_preorder=order.is_preorder,
        total_amount_tiyin=order.total_amount_tiyin,
        delivery_address=order.delivery_address,
        idempotency_key=order.idempotency_key,
        sub_orders=[serialize_sub_order(sub) for sub in order.sub_orders.all()],
    )


@api_router.post(
    "orders",
    response=OrderResponse,
    status_code=201,
    tags=["Orders"],
    summary="B2B savatchani rasmiylashtirish va sotuvchilar bo'yicha SubOrder larga ajratish (Order Splitting)",
    auth=True,
    operation_id="createB2BOrder",
)
def create_order_endpoint(
    request: HttpRequest,
    payload: CreateOrderRequest,
) -> OrderResponse:
    user: User = request.user  # type: ignore[assignment]
    buyer_org = require_roles(user, [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY])
    order = create_b2b_order_with_splitting(
        buyer_org=buyer_org,
        created_by=user,
        items=[item.model_dump() for item in payload.items],
        idempotency_key=payload.idempotency_key,
        delivery_address=payload.delivery_address,
        is_preorder=payload.is_preorder,
    )
    return serialize_order(order)


@api_router.get(
    "orders/waybill/{waybill_qr_token}",
    response=SubOrderResponse,
    status_code=200,
    tags=["Orders"],
    summary="Yuk xati QR-kodi orqali SubOrder tovarlari, MXIK va narxlarini olish (1-Click Avto-Kirim uchun)",
    auth=True,
    operation_id="getSubOrderWaybillByQr",
)
def get_waybill_endpoint(
    request: HttpRequest,
    waybill_qr_token: str,
) -> SubOrderResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(
        user,
        [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY, OrganizationRole.MANUFACTURER],
    )
    sub_order = get_waybill_by_qr_token(waybill_qr_token, viewer_org=org)
    return serialize_sub_order(sub_order)
