"""
Orders Models:
- Order (B2B Buyer Order with total_amount_tiyin BigIntegerField and idempotency_key)
- SubOrder (Automatic Order Splitting per Seller with waybill_qr_token for 1-Click POS Auto-Inbound)
- SubOrderItem (Line items with batch_id and unit_price_tiyin / line_total_tiyin in BigIntegerField)
"""
from __future__ import annotations

import uuid
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.models import Offer, ProductVariant
from apps.iam.models import Organization, User


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "To'lov kutilmoqda"
    CONFIRMED = "CONFIRMED", "Tasdiqlandi (Escrow muzlatildi)"
    IN_TRANSIT = "IN_TRANSIT", "Yo'lda"
    DELIVERED = "DELIVERED", "Topshirildi"
    CANCELLED = "CANCELLED", "Bekor qilindi"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer_org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="buyer_orders",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_orders",
    )
    status = models.CharField(
        max_length=24,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    is_preorder = models.BooleanField(default=False)
    total_amount_tiyin = models.BigIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Jami buyurtma summasi (tiyinlarda)",
    )
    delivery_address = models.TextField(blank=True, default="")
    idempotency_key = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_orders"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount_tiyin__gt=0),
                name="chk_order_total_tiyin_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["buyer_org", "status"], name="idx_order_buyer_status"),
            models.Index(fields=["created_at"], name="idx_order_created_at"),
        ]

    def __str__(self) -> str:
        return f"Order {self.id} ({self.buyer_org.name} - {self.total_amount_tiyin} tiyin)"


class SubOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="sub_orders",
    )
    seller_org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="seller_sub_orders",
    )
    status = models.CharField(
        max_length=24,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    subtotal_amount_tiyin = models.BigIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Ushbu sotuvchi bo'yicha sub-order summasi (tiyinlarda)",
    )
    waybill_qr_token = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="POS 1-Click Avto-Kirim uchun yuk xati QR-tokeni",
    )
    is_pos_inbounded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_sub_orders"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(subtotal_amount_tiyin__gt=0),
                name="chk_suborder_subtotal_tiyin_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["seller_org", "status"], name="idx_suborder_seller_status"),
            models.Index(fields=["waybill_qr_token"], name="idx_suborder_waybill_qr"),
        ]

    def __str__(self) -> str:
        return f"SubOrder {self.id} (Seller: {self.seller_org.name}, {self.subtotal_amount_tiyin} tiyin)"


class SubOrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.ForeignKey(
        SubOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    offer = models.ForeignKey(
        Offer,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    batch_id = models.CharField(max_length=64, default="PREORDER-BATCH")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price_tiyin = models.BigIntegerField(validators=[MinValueValidator(1)])
    line_total_tiyin = models.BigIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        db_table = "orders_sub_order_items"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_price_tiyin__gt=0),
                name="chk_item_unit_price_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(line_total_tiyin__gt=0),
                name="chk_item_line_total_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.variant.sku} x{self.quantity} ({self.line_total_tiyin} tiyin)"
