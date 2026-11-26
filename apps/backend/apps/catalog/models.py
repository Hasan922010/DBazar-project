"""
Catalog Models: Category, Product, ProductVariant (17-digit MXIK, barcode, packaging_coefficient),
Offer, and PriceTier (unit_price_tiyin as BigIntegerField).
Zero FloatField allowed per GEMINI.md rule #3.
"""
from __future__ import annotations

import uuid
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from apps.iam.models import Organization

mxik_17_validator = RegexValidator(
    regex=r"^\d{17}$",
    message="MXIK kodi qat'iy 17 ta raqamdan iborat bo'lishi shart.",
)


class UnitType(models.TextChoices):
    PCS = "PCS", "Dona"
    BOX = "BOX", "Karobka / Blok"
    KG = "KG", "Kilogramm"
    LITER = "LITER", "Litr"


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "catalog_categories"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manufacturer = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="manufactured_products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=128, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_products"
        indexes = [
            models.Index(fields=["manufacturer", "is_active"], name="idx_prod_mfg_active"),
            models.Index(fields=["name"], name="idx_prod_name"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.brand})"


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    mxik_code = models.CharField(max_length=17, validators=[mxik_17_validator], db_index=True)
    barcode = models.CharField(max_length=32, db_index=True)
    unit_type = models.CharField(max_length=16, choices=UnitType.choices, default=UnitType.PCS)
    packaging_coefficient = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="1 qadoqda necha dona borligi",
    )
    weight_grams = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "catalog_product_variants"
        indexes = [
            models.Index(fields=["mxik_code"], name="idx_variant_mxik"),
            models.Index(fields=["barcode"], name="idx_variant_barcode"),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.sku}] MXIK:{self.mxik_code}"


class Offer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    base_price_tiyin = models.BigIntegerField(
        validators=[MinValueValidator(1)],
        help_text="1 birlik uchun bazaviy ulgurji narx (tiyinlarda)",
    )
    min_order_qty = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_offers"
        constraints = [
            models.UniqueConstraint(fields=["seller", "variant"], name="uniq_offer_seller_variant"),
            models.CheckConstraint(
                condition=models.Q(base_price_tiyin__gt=0),
                name="chk_offer_base_price_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["variant", "is_active"], name="idx_offer_variant_active"),
            models.Index(fields=["seller", "is_active"], name="idx_offer_seller_active"),
        ]

    def __str__(self) -> str:
        return f"Offer {self.seller.name} -> {self.variant.sku} ({self.base_price_tiyin} tiyin)"


class PriceTier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name="price_tiers",
    )
    min_qty = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    max_qty = models.PositiveIntegerField(null=True, blank=True)
    unit_price_tiyin = models.BigIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Hajmga qarab 1 birlik narxi (tiyinlarda)",
    )

    class Meta:
        db_table = "catalog_price_tiers"
        ordering = ["min_qty"]
        constraints = [
            models.UniqueConstraint(fields=["offer", "min_qty"], name="uniq_tier_offer_min_qty"),
            models.CheckConstraint(
                condition=models.Q(unit_price_tiyin__gt=0),
                name="chk_tier_unit_price_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Tier >= {self.min_qty}: {self.unit_price_tiyin} tiyin"
