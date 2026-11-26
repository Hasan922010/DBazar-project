"""
Orders Service Layer:
- Multi-vendor B2B Cart Checkout with automatic Order Splitting into seller-specific SubOrders
- Consolidates duplicate offer_id lines and sorts deterministically to apply true Tiered Pricing and prevent deadlocks
- Atomic FEFO stock reservation via Inventory service
- Tenant-isolated Waybill QR lookup for 1-Click POS Auto-Inbound
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Q

from apps.catalog.models import Offer
from apps.catalog.services import calculate_offer_price_for_qty
from apps.iam.models import Organization, OrganizationRole, User
from apps.inventory.services import reserve_seller_stock_fefo
from apps.orders.models import Order, OrderStatus, SubOrder, SubOrderItem
from config.api_router import ApiError


@transaction.atomic
def create_b2b_order_with_splitting(
    *,
    buyer_org: Organization,
    created_by: User,
    items: List[Dict[str, object]],
    idempotency_key: uuid.UUID,
    delivery_address: str = "",
    is_preorder: bool = False,
) -> Order:
    """
    Idempotently creates a B2B Order and splits it by seller Organization into SubOrders.
    Merges duplicate offer_id rows and sorts by offer_id so Tiered Pricing is accurate and row locks never deadlock.
    """
    existing = (
        Order.objects.prefetch_related("sub_orders__items__variant__product", "sub_orders__seller_org")
        .filter(idempotency_key=idempotency_key)
        .first()
    )
    if existing is not None:
        if existing.buyer_org_id != buyer_org.id:
            raise ApiError(409, "IDEMPOTENCY_KEY_CONFLICT", "Idempotency kaliti boshqa xaridor tomonidan ishlatilgan.")
        return existing

    if not items:
        raise ApiError(400, "EMPTY_CART", "Savatcha bo'sh bo'lishi mumkin emas.")

    # Merge duplicate offer_id quantities and sort deterministically by offer_id
    merged_quantities: Dict[uuid.UUID, int] = defaultdict(int)
    for raw_item in items:
        offer_id = uuid.UUID(str(raw_item["offer_id"]))
        merged_quantities[offer_id] += int(raw_item["quantity"])  # type: ignore[arg-type]

    ordered_offer_ids = sorted(merged_quantities.keys(), key=str)
    offers_map = {
        o.id: o
        for o in Offer.objects.select_related("seller", "variant", "variant__product")
        .prefetch_related("price_tiers")
        .filter(id__in=ordered_offer_ids, is_active=True)
    }

    seller_buckets: Dict[uuid.UUID, List[tuple[Offer, int, int, int, List[tuple[str, int]]]]] = defaultdict(list)
    grand_total_tiyin = 0

    for offer_id in ordered_offer_ids:
        offer = offers_map.get(offer_id)
        if offer is None:
            raise ApiError(404, "OFFER_NOT_FOUND", f"Taklif topilmadi: {offer_id}")

        qty = merged_quantities[offer_id]
        unit_price_tiyin, line_total_tiyin = calculate_offer_price_for_qty(offer, qty)
        grand_total_tiyin += line_total_tiyin

        if is_preorder:
            batch_allocations = [("PREORDER-BATCH", qty)]
        else:
            reserved_stocks = reserve_seller_stock_fefo(
                seller_org=offer.seller,
                variant_id=offer.variant_id,
                required_qty=qty,
            )
            batch_allocations = [(stock.batch_id, alloc_qty) for stock, alloc_qty in reserved_stocks]

        seller_buckets[offer.seller_id].append(
            (offer, qty, unit_price_tiyin, line_total_tiyin, batch_allocations)
        )

    order = Order.objects.create(
        buyer_org=buyer_org,
        created_by=created_by,
        status=OrderStatus.PENDING,
        is_preorder=is_preorder,
        total_amount_tiyin=grand_total_tiyin,
        delivery_address=delivery_address or buyer_org.address,
        idempotency_key=idempotency_key,
    )

    for _, bucket in seller_buckets.items():
        seller_org = bucket[0][0].seller
        subtotal_tiyin = sum(entry[3] for entry in bucket)
        waybill_token = f"WB-{uuid.uuid4().hex[:16].upper()}"

        sub_order = SubOrder.objects.create(
            order=order,
            seller_org=seller_org,
            status=OrderStatus.PENDING,
            subtotal_amount_tiyin=subtotal_tiyin,
            waybill_qr_token=waybill_token,
        )

        for offer, _, unit_price_tiyin, _, batch_allocations in bucket:
            for batch_id, alloc_qty in batch_allocations:
                SubOrderItem.objects.create(
                    sub_order=sub_order,
                    offer=offer,
                    variant=offer.variant,
                    batch_id=batch_id,
                    quantity=alloc_qty,
                    unit_price_tiyin=unit_price_tiyin,
                    line_total_tiyin=unit_price_tiyin * alloc_qty,
                )

    return (
        Order.objects.prefetch_related("sub_orders__items__variant__product", "sub_orders__seller_org")
        .get(id=order.id)
    )


def get_waybill_by_qr_token(waybill_qr_token: str, viewer_org: Optional[Organization] = None) -> SubOrder:
    qs = SubOrder.objects.select_related("order", "order__buyer_org", "seller_org").prefetch_related(
        "items__variant__product"
    )
    if viewer_org is not None and viewer_org.role != OrganizationRole.ADMIN:
        qs = qs.filter(Q(order__buyer_org=viewer_org) | Q(seller_org=viewer_org))
    sub_order = qs.filter(waybill_qr_token=waybill_qr_token).first()
    if sub_order is None:
        raise ApiError(404, "WAYBILL_NOT_FOUND", "Yuk xati QR-kodi topilmadi yoki sizga tegishli emas.")
    return sub_order
