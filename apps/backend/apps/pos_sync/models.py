"""
POS Sync Models (GEMINI.md Rule #4):
- PosStore
- PosShift
- PosSale
- PosStockEvent (Immutable append-only delta log: INBOUND, SALE, RETURN, WRITE_OFF with HLC timestamp)
No direct `UPDATE stock SET qty = X` is allowed from POS clients.
"""
from __future__ import annotations

import uuid
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.models import ProductVariant
from apps.iam.models import Organization, User


class PosStockEventType(models.TextChoices):
    INBOUND = "INBOUND", "Tovar kirimi (+)"
    SALE = "SALE", "Kassa sotuvi (-)"
    RETURN = "RETURN", "Xaridordan qaytarish (+)"
    WRITE_OFF = "WRITE_OFF", "Hisobdan chiqarish / Yaroqsiz (-)"


class PosPaymentMethod(models.TextChoices):
    CASH = "CASH", "Naqd"
    CARD = "CARD", "Plastik karta"
    MIXED = "MIXED", "Aralash"
    NASIYA = "NASIYA", "Nasiya daftari"


class PosStore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="pos_stores",
    )
    name = models.CharField(max_length=255)
    terminal_id = models.CharField(max_length=64, unique=True)
    address = models.TextField(blank=True, default="")
    last_hlc_timestamp = models.CharField(max_length=128, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pos_stores"
        indexes = [
            models.Index(fields=["organization", "is_active"], name="idx_pos_store_org_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.terminal_id})"


class PosShift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        PosStore,
        on_delete=models.CASCADE,
        related_name="shifts",
    )
    cashier = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pos_shifts",
    )
    opening_cash_tiyin = models.BigIntegerField(default=0, validators=[MinValueValidator(0)])
    closing_cash_tiyin = models.BigIntegerField(default=0, validators=[MinValueValidator(0)])
    is_open = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pos_shifts"


class PosSale(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        PosStore,
        on_delete=models.CASCADE,
        related_name="sales",
    )
    shift = models.ForeignKey(
        PosShift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    client_sale_id = models.UUIDField(unique=True)
    receipt_seq = models.PositiveIntegerField()
    payment_method = models.CharField(
        max_length=16,
        choices=PosPaymentMethod.choices,
        default=PosPaymentMethod.CASH,
    )
    total_amount_tiyin = models.BigIntegerField(validators=[MinValueValidator(1)])
    fiscal_sign = models.CharField(max_length=64, blank=True, default="")
    fiscal_qr_url = models.URLField(blank=True, default="")
    hlc_timestamp = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pos_sales"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount_tiyin__gt=0),
                name="chk_pos_sale_total_positive",
            ),
        ]


class PosStockEvent(models.Model):
    """
    Append-only POS inventory delta record with Hybrid Logical Clock (HLC) ordering.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        PosStore,
        on_delete=models.CASCADE,
        related_name="stock_events",
    )
    client_event_id = models.UUIDField(
        unique=True,
        help_text="Idempotency UUID generated on offline POS SQLite device",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="pos_stock_events",
    )
    batch_id = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(max_length=16, choices=PosStockEventType.choices)
    qty_delta = models.IntegerField(
        help_text="Positive for INBOUND/RETURN, negative for SALE/WRITE_OFF",
    )
    unit_price_tiyin = models.BigIntegerField(default=0, validators=[MinValueValidator(0)])
    hlc_timestamp = models.CharField(max_length=128, db_index=True)
    waybill_qr_token = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pos_stock_events"
        indexes = [
            models.Index(fields=["store", "hlc_timestamp"], name="idx_pos_evt_store_hlc"),
            models.Index(fields=["variant", "batch_id"], name="idx_pos_evt_variant_batch"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} {self.qty_delta} [{self.variant.sku}] HLC:{self.hlc_timestamp}"
