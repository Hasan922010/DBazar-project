"""
Logistics Service Layer:
- Shipment creation & driver assignment
- Real-time GPS coordinate logging (integer microdegrees)
- Single-button driver status transitions ("Ombordan oldim" -> "Yo'lga chiqdim" -> "Topshirdim")
- Proof of Delivery (OTP/QR + Photo) verification with automatic Escrow Split Settlement trigger
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.billing.services import release_escrow_split_settlement
from apps.iam.models import Organization, User
from apps.logistics.models import Shipment, ShipmentStatus, TrackingLog
from apps.orders.models import OrderStatus, SubOrder
from config.api_router import ApiError


def _generate_deterministic_otp(sub_order_id: uuid.UUID) -> str:
    digest = hashlib.sha256(f"POD-OTP:{sub_order_id}".encode("utf-8")).hexdigest()
    return str(int(digest[:8], 16) % 900000 + 100000)


@transaction.atomic
def create_or_assign_shipment(
    *,
    sub_order_id: uuid.UUID,
    logistics_org: Optional[Organization],
    driver: Optional[User] = None,
) -> Shipment:
    sub_order = SubOrder.objects.select_for_update().filter(id=sub_order_id).first()
    if sub_order is None:
        raise ApiError(404, "SUBORDER_NOT_FOUND", "SubOrder topilmadi.")

    shipment, created = Shipment.objects.get_or_create(
        sub_order=sub_order,
        defaults={
            "logistics_org": logistics_org,
            "driver": driver,
            "status": ShipmentStatus.ASSIGNED,
            "pod_otp_code": _generate_deterministic_otp(sub_order.id),
        },
    )
    if not created and driver is not None:
        shipment.driver = driver
        shipment.logistics_org = logistics_org
        shipment.save(update_fields=["driver", "logistics_org", "updated_at"])
    return shipment


@transaction.atomic
def update_shipment_gps_and_status(
    *,
    shipment_id: uuid.UUID,
    lat_microdeg: int,
    lng_microdeg: int,
    new_status: Optional[str] = None,
) -> Shipment:
    shipment = Shipment.objects.select_for_update().select_related("sub_order").filter(id=shipment_id).first()
    if shipment is None:
        raise ApiError(404, "SHIPMENT_NOT_FOUND", "Yetkazib berish yozuvi topilmadi.")

    shipment.current_lat_microdeg = lat_microdeg
    shipment.current_lng_microdeg = lng_microdeg
    if new_status in (ShipmentStatus.PICKED_UP, ShipmentStatus.IN_TRANSIT):
        shipment.status = new_status
        shipment.sub_order.status = OrderStatus.IN_TRANSIT
        shipment.sub_order.save(update_fields=["status", "updated_at"])

    shipment.save(update_fields=["current_lat_microdeg", "current_lng_microdeg", "status", "updated_at"])
    TrackingLog.objects.create(
        shipment=shipment,
        lat_microdeg=lat_microdeg,
        lng_microdeg=lng_microdeg,
    )
    return shipment


@transaction.atomic
def confirm_shipment_pod_and_release_escrow(
    *,
    shipment_id: uuid.UUID,
    pod_otp_code: str,
    release_idempotency_key: uuid.UUID,
    pod_photo_url: str = "",
) -> Shipment:
    shipment = Shipment.objects.select_for_update().select_related("sub_order").filter(id=shipment_id).first()
    if shipment is None:
        raise ApiError(404, "SHIPMENT_NOT_FOUND", "Yetkazib berish yozuvi topilmadi.")

    if shipment.pod_otp_code != pod_otp_code:
        raise ApiError(400, "INVALID_POD_OTP", "Tasdiqlash OTP kodi noto'g'ri.")

    if shipment.status != ShipmentStatus.DELIVERED:
        shipment.status = ShipmentStatus.DELIVERED
        shipment.pod_photo_url = pod_photo_url
        shipment.delivered_at = timezone.now()
        shipment.save(update_fields=["status", "pod_photo_url", "delivered_at", "updated_at"])

    # Trigger Escrow Split Settlement & VMI Lineage update
    release_escrow_split_settlement(
        sub_order_id=shipment.sub_order_id,
        idempotency_key=release_idempotency_key,
    )
    return shipment
