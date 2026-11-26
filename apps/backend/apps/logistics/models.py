"""
Logistics Models:
- Shipment (Lite-TMS shipment lifecycle: Ombordan oldim -> Yo'lga chiqdim -> Topshirdim + OTP/QR POD)
- TrackingLog (Real-time GPS coordinates stored in integer microdegrees to ensure zero FloatField)
"""
from __future__ import annotations

import uuid
from django.db import models

from apps.iam.models import Organization, User
from apps.orders.models import SubOrder


class ShipmentStatus(models.TextChoices):
    ASSIGNED = "ASSIGNED", "Haydovchiga biriktirildi"
    PICKED_UP = "PICKED_UP", "Ombordan oldim"
    IN_TRANSIT = "IN_TRANSIT", "Yo'lga chiqdim"
    DELIVERED = "DELIVERED", "Topshirdim (POD tasdiqlandi)"


class Shipment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.OneToOneField(
        SubOrder,
        on_delete=models.CASCADE,
        related_name="shipment",
    )
    logistics_org = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipments",
    )
    driver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_shipments",
    )
    status = models.CharField(
        max_length=24,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.ASSIGNED,
    )
    pod_otp_code = models.CharField(max_length=6, help_text="6 xonali SMS/OTP tasdiqlash kodi")
    current_lat_microdeg = models.IntegerField(
        default=41311081,
        help_text="Kenglik (latitude * 1_000_000, masalan 41.311081 -> 41311081)",
    )
    current_lng_microdeg = models.IntegerField(
        default=69240562,
        help_text="Uzunlik (longitude * 1_000_000, masalan 69.240562 -> 69240562)",
    )
    pod_photo_url = models.URLField(blank=True, default="")
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "logistics_shipments"
        indexes = [
            models.Index(fields=["driver", "status"], name="idx_shipment_driver_status"),
        ]


class TrackingLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="tracking_logs",
    )
    lat_microdeg = models.IntegerField()
    lng_microdeg = models.IntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "logistics_tracking_logs"
        indexes = [
            models.Index(fields=["shipment", "recorded_at"], name="idx_track_shipment_time"),
        ]
