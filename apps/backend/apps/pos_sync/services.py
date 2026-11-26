"""
POS Sync Service Layer:
- HLC-ordered append-only delta event ingestion (`INBOUND`, `SALE`, `RETURN`, `WRITE_OFF`)
- Batched SQL queries (`bulk_create` + aggregated `InventoryLineage` updates) for 1,000+ RPS scale
- Monotonic HLC watermark comparison so delayed packets never rewind `last_hlc_timestamp`
- 1-Click Auto-Inbound by scanning B2B SubOrder `waybill_qr_token`
"""
from __future__ import annotations

from collections import defaultdict
import uuid
from typing import Any, Dict, List

from django.db import transaction

from apps.catalog.models import ProductVariant
from apps.iam.models import Organization
from apps.inventory.models import InventoryLineage
from apps.inventory.services import record_supply_lineage
from apps.orders.models import SubOrder
from apps.pos_sync.models import PosStockEvent, PosStockEventType, PosStore
from config.api_router import ApiError
from config.hlc import generate_hlc_timestamp, parse_hlc_timestamp


@transaction.atomic
def create_pos_store(
    *,
    organization: Organization,
    name: str,
    terminal_id: str,
    address: str = "",
) -> PosStore:
    if PosStore.objects.filter(terminal_id=terminal_id).exists():
        raise ApiError(409, "TERMINAL_EXISTS", f"Terminal ID '{terminal_id}' allaqachon mavjud.")
    return PosStore.objects.create(
        organization=organization,
        name=name,
        terminal_id=terminal_id,
        address=address,
    )


def _normalize_signed_delta(event_type: str, raw_qty: int) -> int:
    abs_qty = abs(int(raw_qty))
    if abs_qty == 0:
        raise ApiError(400, "ZERO_QTY_DELTA", "Harakat miqdori 0 bo'lishi mumkin emas.")
    if event_type in (PosStockEventType.INBOUND, PosStockEventType.RETURN):
        return abs_qty
    if event_type in (PosStockEventType.SALE, PosStockEventType.WRITE_OFF):
        return -abs_qty
    raise ApiError(400, "INVALID_EVENT_TYPE", f"Noma'lum hodisa turi: {event_type}")


def _is_newer_hlc(candidate_hlc: str, current_hlc: str) -> bool:
    if not candidate_hlc:
        return False
    if not current_hlc:
        return True
    return parse_hlc_timestamp(candidate_hlc) > parse_hlc_timestamp(current_hlc)


@transaction.atomic
def ingest_pos_delta_events(
    *,
    customer_org: Organization,
    store_id: uuid.UUID,
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Processes a batch of offline POS delta events ordered by HLC timestamp.
    Uses batched variant lookup, `bulk_create`, and per-SKU aggregated `InventoryLineage` updates.
    """
    store = PosStore.objects.select_for_update().filter(
        id=store_id,
        organization=customer_org,
        is_active=True,
    ).first()
    if store is None:
        raise ApiError(404, "POS_STORE_NOT_FOUND", "POS do'koni topilmadi yoki sizga tegishli emas.")

    parsed_events: List[tuple[tuple[int, int, str], Dict[str, Any]]] = []
    for ev in events:
        try:
            hlc_tuple = parse_hlc_timestamp(str(ev["hlc_timestamp"]))
        except ValueError as exc:
            raise ApiError(400, "INVALID_HLC_TIMESTAMP", str(exc)) from exc
        parsed_events.append((hlc_tuple, ev))

    parsed_events.sort(key=lambda pair: pair[0])

    incoming_ids = [uuid.UUID(str(pair[1]["client_event_id"])) for pair in parsed_events]
    existing_ids = set(
        PosStockEvent.objects.filter(client_event_id__in=incoming_ids).values_list("client_event_id", flat=True)
    )

    needed_variant_ids = {uuid.UUID(str(pair[1]["variant_id"])) for pair in parsed_events}
    variants_map = {
        v.id: v
        for v in ProductVariant.objects.select_related("product").filter(id__in=needed_variant_ids)
    }

    events_to_create: List[PosStockEvent] = []
    # (variant_id, batch_id) -> [net_qty_delta, supplied_delta, net_sold_delta]
    lineage_deltas: Dict[tuple[uuid.UUID, str], List[int]] = defaultdict(lambda: [0, 0, 0])
    skipped_duplicates = 0
    max_hlc = store.last_hlc_timestamp

    for _, ev in parsed_events:
        client_event_id = uuid.UUID(str(ev["client_event_id"]))
        if client_event_id in existing_ids:
            skipped_duplicates += 1
            continue

        variant_id = uuid.UUID(str(ev["variant_id"]))
        variant = variants_map.get(variant_id)
        if variant is None:
            raise ApiError(404, "VARIANT_NOT_FOUND", f"Tovar varianti topilmadi: {variant_id}")

        event_type = str(ev["event_type"])
        qty_delta = _normalize_signed_delta(event_type, int(ev["quantity"]))
        batch_id = str(ev.get("batch_id") or "DEFAULT-BATCH")
        unit_price_tiyin = int(ev.get("unit_price_tiyin") or 0)
        hlc_str = str(ev["hlc_timestamp"])

        events_to_create.append(
            PosStockEvent(
                store=store,
                client_event_id=client_event_id,
                variant=variant,
                batch_id=batch_id,
                event_type=event_type,
                qty_delta=qty_delta,
                unit_price_tiyin=unit_price_tiyin,
                hlc_timestamp=hlc_str,
                waybill_qr_token=str(ev.get("waybill_qr_token") or ""),
            )
        )
        existing_ids.add(client_event_id)
        if _is_newer_hlc(hlc_str, max_hlc):
            max_hlc = hlc_str

        acc = lineage_deltas[(variant_id, batch_id)]
        acc[0] += qty_delta
        if event_type == PosStockEventType.INBOUND:
            acc[1] += qty_delta
        elif event_type == PosStockEventType.SALE:
            acc[2] += abs(qty_delta)
        elif event_type == PosStockEventType.RETURN:
            acc[2] -= abs(qty_delta)

    if events_to_create:
        PosStockEvent.objects.bulk_create(events_to_create)

    if lineage_deltas:
        existing_lineages = {
            (ln.variant_id, ln.batch_id): ln
            for ln in InventoryLineage.objects.select_for_update().filter(
                customer_org=customer_org,
                variant_id__in=[vid for vid, _ in lineage_deltas.keys()],
            )
        }
        for (variant_id, batch_id), (net_qty, supplied_add, sold_delta) in sorted(
            lineage_deltas.items(), key=lambda item: (str(item[0][0]), item[0][1])
        ):
            variant = variants_map[variant_id]
            lineage = existing_lineages.get((variant_id, batch_id))
            if lineage is None:
                InventoryLineage.objects.create(
                    variant=variant,
                    batch_id=batch_id,
                    manufacturer_org=variant.product.manufacturer,
                    intermediary_org=None,
                    customer_org=customer_org,
                    supplied_qty=max(supplied_add, 0),
                    current_pos_qty=net_qty,
                    sold_pos_qty=max(0, sold_delta),
                )
            else:
                lineage.current_pos_qty += net_qty
                lineage.supplied_qty += supplied_add
                lineage.sold_pos_qty = max(0, lineage.sold_pos_qty + sold_delta)
                lineage.save(update_fields=["supplied_qty", "current_pos_qty", "sold_pos_qty", "updated_at"])

    if _is_newer_hlc(max_hlc, store.last_hlc_timestamp):
        store.last_hlc_timestamp = max_hlc
        store.save(update_fields=["last_hlc_timestamp"])

    return {
        "store_id": store.id,
        "applied_events": len(events_to_create),
        "skipped_duplicates": skipped_duplicates,
        "conflicts": 0,
        "last_hlc_timestamp": store.last_hlc_timestamp,
    }


@transaction.atomic
def execute_one_click_waybill_inbound(
    *,
    customer_org: Organization,
    store_id: uuid.UUID,
    waybill_qr_token: str,
) -> Dict[str, Any]:
    """
    1-Click Auto-Inbound:
    Scans the QR code on a DBazar B2B SubOrder waybill and automatically creates append-only
    INBOUND PosStockEvents and InventoryLineage records in 1 click. Idempotent if scanned twice.
    """
    store = PosStore.objects.select_for_update().filter(
        id=store_id,
        organization=customer_org,
        is_active=True,
    ).first()
    if store is None:
        raise ApiError(404, "POS_STORE_NOT_FOUND", "POS do'koni topilmadi.")

    sub_order = (
        SubOrder.objects.select_for_update()
        .select_related("order", "seller_org")
        .prefetch_related("items__variant__product")
        .filter(waybill_qr_token=waybill_qr_token, order__buyer_org=customer_org)
        .first()
    )
    if sub_order is None:
        raise ApiError(404, "WAYBILL_NOT_FOUND", "Yuk xati QR-kodi topilmadi yoki ushbu do'konga tegishli emas.")

    items = list(sub_order.items.all())
    hlc = store.last_hlc_timestamp or None
    inbounded_count = 0

    for item in items:
        deterministic_event_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"dbazar:1click-inbound:{store.id}:{sub_order.id}:{item.id}",
        )
        if PosStockEvent.objects.filter(client_event_id=deterministic_event_id).exists():
            continue

        hlc = generate_hlc_timestamp(node_id=store.terminal_id, last_hlc=hlc)
        PosStockEvent.objects.create(
            store=store,
            client_event_id=deterministic_event_id,
            variant=item.variant,
            batch_id=item.batch_id,
            event_type=PosStockEventType.INBOUND,
            qty_delta=item.quantity,
            unit_price_tiyin=item.unit_price_tiyin,
            hlc_timestamp=hlc,
            waybill_qr_token=waybill_qr_token,
        )
        record_supply_lineage(
            variant=item.variant,
            batch_id=item.batch_id,
            customer_org=customer_org,
            supplied_qty=item.quantity,
            manufacturer_org=item.variant.product.manufacturer,
            intermediary_org=sub_order.seller_org,
        )
        inbounded_count += 1

    if hlc and _is_newer_hlc(hlc, store.last_hlc_timestamp):
        store.last_hlc_timestamp = hlc
        store.save(update_fields=["last_hlc_timestamp"])

    if not sub_order.is_pos_inbounded:
        sub_order.is_pos_inbounded = True
        sub_order.save(update_fields=["is_pos_inbounded", "updated_at"])

    return {
        "store_id": store.id,
        "sub_order_id": sub_order.id,
        "waybill_qr_token": waybill_qr_token,
        "inbounded_items_count": inbounded_count,
        "total_waybill_items": len(items),
        "is_pos_inbounded": True,
    }
