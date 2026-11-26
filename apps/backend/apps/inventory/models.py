"""
Inventory Models:
- Warehouse
- InventoryStock (FEFO batch & expiry tracking, atomic select_for_update reservation)
- InventoryLineage (manufacturer -> intermediary -> customer_pos supply chain tracking)
- PosTelemetryPermission (strict VMI tenant & batch isolation)
"""
from __future__ import annotations

import uuid
from django.db import models

from apps.catalog.models import ProductVariant
from apps.iam.models import Organization


class Warehouse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="warehouses",
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, unique=True)
    region = models.CharField(max_length=100, default="Toshkent")
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_warehouses"
        indexes = [
            models.Index(fields=["organization", "is_active"], name="idx_wh_org_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class InventoryStock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stocks",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="warehouse_stocks",
    )
    batch_id = models.CharField(max_length=64, db_index=True)
    available_qty = models.IntegerField(default=0)
    reserved_qty = models.IntegerField(default=0)
    min_stock_threshold = models.PositiveIntegerField(default=10)
    expiry_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_stocks"
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "variant", "batch_id"],
                name="uniq_stock_wh_variant_batch",
            ),
            models.CheckConstraint(
                condition=models.Q(available_qty__gte=0),
                name="chk_stock_available_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_qty__gte=0),
                name="chk_stock_reserved_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["warehouse", "variant"], name="idx_stock_wh_variant"),
            models.Index(fields=["batch_id"], name="idx_stock_batch"),
        ]

    def __str__(self) -> str:
        return f"{self.warehouse.code} | {self.variant.sku} | Batch:{self.batch_id} (Avail:{self.available_qty})"


class InventoryLineage(models.Model):
    """
    Tracks multi-tier supply chain lineage: Manufacturer -> Intermediary -> Customer POS Store.
    Updated when B2B orders are delivered/inbounded and when POS delta events arrive.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="lineages",
    )
    batch_id = models.CharField(max_length=64, db_index=True)
    manufacturer_org = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufactured_lineages",
    )
    intermediary_org = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="distributed_lineages",
    )
    customer_org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="customer_lineages",
    )
    supplied_qty = models.IntegerField(default=0)
    current_pos_qty = models.IntegerField(default=0)
    sold_pos_qty = models.IntegerField(default=0)
    min_restock_threshold = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_lineages"
        constraints = [
            models.UniqueConstraint(
                fields=["customer_org", "variant", "batch_id"],
                name="uniq_lineage_customer_variant_batch",
            ),
        ]
        indexes = [
            models.Index(fields=["intermediary_org", "customer_org"], name="idx_lineage_interm_cust"),
            models.Index(fields=["manufacturer_org", "customer_org"], name="idx_lineage_mfg_cust"),
            models.Index(fields=["batch_id"], name="idx_lineage_batch"),
        ]

    @property
    def traffic_light_status(self) -> str:
        """Minimalist traffic light indicator: RED (tugamoqda), YELLOW (kamaydi), GREEN (yetarli)."""
        if self.current_pos_qty <= self.min_restock_threshold:
            return "RED"
        if self.current_pos_qty <= self.min_restock_threshold * 2:
            return "YELLOW"
        return "GREEN"


class PosTelemetryPermission(models.Model):
    """
    VMI Isolation Rule (GEMINI.md #5):
    An intermediary or manufacturer can ONLY view a customer store's POS stock & sales telemetry if:
    1) An active PosTelemetryPermission exists from customer_org to viewer_org
    2) The InventoryLineage record proves viewer_org supplied that SKU/batch_id.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="granted_telemetry_permissions",
    )
    viewer_org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="received_telemetry_permissions",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Agar bo'sh bo'lsa, viewer_org yetkazib bergan barcha tovarlar uchun amal qiladi.",
    )
    batch_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Agar bo'sh bo'lsa, viewer_org yetkazib bergan barcha partiyalar uchun amal qiladi.",
    )
    is_active = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "inventory_pos_telemetry_permissions"
        indexes = [
            models.Index(fields=["viewer_org", "customer_org", "is_active"], name="idx_vmi_perm_viewer_cust"),
        ]

    def __str__(self) -> str:
        return f"VMI Perm: {self.customer_org.name} -> {self.viewer_org.name} (active={self.is_active})"
