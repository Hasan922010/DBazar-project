"""
Orders REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

import uuid
from django.http import HttpRequest

from apps.iam.models import OrganizationRole, User
from apps.iam.services import require_roles
from apps.orders.models import Order, RfqTender, SubOrder
from apps.orders.schemas import (
    CreateOrderRequest,
    CreateRfqTenderRequest,
    OrderListResponse,
    OrderResponse,
    RfqBidResponse,
    RfqTenderListResponse,
    RfqTenderResponse,
    SubOrderItemResponse,
    SubOrderResponse,
    SubmitRfqBidRequest,
)
from apps.orders.services import (
    award_best_rfq_bid,
    cancel_pending_order,
    create_b2b_order_with_splitting,
    create_rfq_tender,
    get_waybill_by_qr_token,
    submit_sealed_rfq_bid,
)
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
    "orders",
    response=OrderListResponse,
    status_code=200,
    tags=["Orders"],
    summary="Tashkilotning B2B buyurtmalar ro'yxatini olish (Tenant-Isolated)",
    auth=True,
    operation_id="listB2BOrders",
)
def list_orders_endpoint(request: HttpRequest) -> OrderListResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(
        user,
        [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY, OrganizationRole.MANUFACTURER],
    )
    qs = Order.objects.prefetch_related("sub_orders__items__variant__product", "sub_orders__seller_org")
    if org.role == OrganizationRole.CUSTOMER:
        qs = qs.filter(buyer_org=org)
    elif org.role != OrganizationRole.ADMIN:
        qs = qs.filter(sub_orders__seller_org=org).distinct()
    return OrderListResponse(items=[serialize_order(o) for o in qs.order_by("-created_at")[:50]])


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


@api_router.post(
    "orders/{order_id}/cancel",
    response=OrderResponse,
    status_code=200,
    tags=["Orders"],
    summary="To'lanmagan (PENDING) buyurtmani bekor qilish va zahiradagi ombor qoldig'ini qaytarish",
    auth=True,
    operation_id="cancelPendingB2BOrder",
)
def cancel_order_endpoint(
    request: HttpRequest,
    order_id: str,
) -> OrderResponse:
    user: User = request.user  # type: ignore[assignment]
    buyer_org = require_roles(user, [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY])
    order = cancel_pending_order(
        buyer_org=buyer_org,
        order_id=uuid.UUID(order_id),
    )
    return serialize_order(order)


@api_router.post(
    "orders/rfq/tenders",
    response=RfqTenderResponse,
    status_code=201,
    tags=["Tender (RFQ)"],
    summary="Yirik xaridorlar uchun yopiq narx taklifli Tender (RFQ) e'lon qilish",
    auth=True,
    operation_id="createRfqTender",
)
def create_rfq_tender_endpoint(
    request: HttpRequest,
    payload: CreateRfqTenderRequest,
) -> RfqTenderResponse:
    user: User = request.user  # type: ignore[assignment]
    buyer_org = require_roles(user, [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY])
    tender = create_rfq_tender(
        buyer_org=buyer_org,
        variant_id=payload.variant_id,
        target_quantity=payload.target_quantity,
        max_unit_price_tiyin=payload.max_unit_price_tiyin,
        region=payload.region,
    )
    return RfqTenderResponse.model_validate(tender)


@api_router.get(
    "orders/rfq/tenders",
    response=RfqTenderListResponse,
    status_code=200,
    tags=["Tender (RFQ)"],
    summary="Ochiq va yakunlangan B2B Tenderlar (RFQ) ro'yxatini olish",
    auth=True,
    operation_id="listRfqTenders",
)
def list_rfq_tenders_endpoint(request: HttpRequest) -> RfqTenderListResponse:
    tenders = list(RfqTender.objects.all().order_by("-created_at")[:50])
    return RfqTenderListResponse(items=[RfqTenderResponse.model_validate(t) for t in tenders])


@api_router.post(
    "orders/rfq/tenders/{tender_id}/bids",
    response=RfqBidResponse,
    status_code=201,
    tags=["Tender (RFQ)"],
    summary="Tenderga yopiq narx taklifi (Sealed Bid) yuborish (raqobatchilardan izolyatsiyalangan)",
    auth=True,
    operation_id="submitSealedRfqBid",
)
def submit_rfq_bid_endpoint(
    request: HttpRequest,
    tender_id: str,
    payload: SubmitRfqBidRequest,
) -> RfqBidResponse:
    user: User = request.user  # type: ignore[assignment]
    seller_org = require_roles(user, [OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY])
    bid = submit_sealed_rfq_bid(
        seller_org=seller_org,
        tender_id=uuid.UUID(tender_id),
        proposed_unit_price_tiyin=payload.proposed_unit_price_tiyin,
    )
    return RfqBidResponse.model_validate(bid)


@api_router.post(
    "orders/rfq/tenders/{tender_id}/award",
    response=OrderResponse,
    status_code=200,
    tags=["Tender (RFQ)"],
    summary="Tenderda eng arzon taklifni g'olib deb topish va 1 bosishda B2B buyurtma yaratish",
    auth=True,
    operation_id="awardRfqTenderBestBid",
)
def award_rfq_tender_endpoint(
    request: HttpRequest,
    tender_id: str,
) -> OrderResponse:
    user: User = request.user  # type: ignore[assignment]
    buyer_org = require_roles(user, [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY])
    order = award_best_rfq_bid(
        buyer_org=buyer_org,
        buyer_user=user,
        tender_id=uuid.UUID(tender_id),
    )
    return serialize_order(order)
