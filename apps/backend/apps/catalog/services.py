"""
Catalog Service Layer: Product & Variant creation (with 17-digit MXIK verification),
Offer & Tiered Pricing calculation in integer tiyin.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Q

from apps.catalog.models import Category, Offer, PriceTier, Product, ProductVariant
from apps.iam.models import Organization, OrganizationRole
from apps.iam.services import UzGovSandboxEmulator
from config.api_router import ApiError


@transaction.atomic
def create_product_with_variant(
    *,
    manufacturer: Organization,
    name: str,
    brand: str,
    description: str,
    sku: str,
    variant_name: str,
    mxik_code: str,
    barcode: str,
    unit_type: str = "PCS",
    packaging_coefficient: int = 1,
    weight_grams: int = 0,
    category_slug: Optional[str] = None,
) -> tuple[Product, ProductVariant]:
    if manufacturer.role not in (OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY, OrganizationRole.ADMIN):
        raise ApiError(403, "FORBIDDEN_ROLE", "Faqat Ishlab chiqaruvchi yoki Vositachi tovar yarata oladi.")

    mxik_check = UzGovSandboxEmulator.verify_mxik(mxik_code)
    if not mxik_check["valid"]:
        raise ApiError(400, "INVALID_MXIK_CODE", mxik_check["error"])

    if ProductVariant.objects.filter(sku=sku).exists():
        raise ApiError(409, "SKU_ALREADY_EXISTS", f"SKU '{sku}' allaqachon mavjud.")

    category = None
    if category_slug:
        category, _ = Category.objects.get_or_create(
            slug=category_slug,
            defaults={"name": category_slug.replace("-", " ").title()},
        )

    product = Product.objects.create(
        manufacturer=manufacturer,
        category=category,
        name=name,
        brand=brand,
        description=description,
    )
    variant = ProductVariant.objects.create(
        product=product,
        sku=sku,
        name=variant_name,
        mxik_code=mxik_code,
        barcode=barcode,
        unit_type=unit_type,
        packaging_coefficient=packaging_coefficient,
        weight_grams=weight_grams,
    )
    variant.full_clean()
    return product, variant


@transaction.atomic
def upsert_offer_with_price_tiers(
    *,
    seller: Organization,
    variant_id: uuid.UUID,
    base_price_tiyin: int,
    min_order_qty: int = 1,
    tiers: Optional[List[Dict[str, Optional[int]]]] = None,
) -> Offer:
    if seller.role not in (OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY, OrganizationRole.ADMIN):
        raise ApiError(403, "FORBIDDEN_ROLE", "Faqat sotuvchi tashkilotlar taklif (Offer) joylay oladi.")
    if base_price_tiyin <= 0:
        raise ApiError(400, "INVALID_PRICE", "Narx 0 tiyindan katta bo'lishi shart.")

    variant = ProductVariant.objects.filter(id=variant_id, is_active=True).first()
    if variant is None:
        raise ApiError(404, "VARIANT_NOT_FOUND", "Tovar varianti topilmadi.")

    offer, _ = Offer.objects.update_or_create(
        seller=seller,
        variant=variant,
        defaults={
            "base_price_tiyin": base_price_tiyin,
            "min_order_qty": min_order_qty,
            "is_active": True,
        },
    )

    if tiers is not None:
        offer.price_tiers.all().delete()
        for tier in tiers:
            min_qty = int(tier["min_qty"] or 1)
            max_qty = int(tier["max_qty"]) if tier.get("max_qty") is not None else None
            unit_price = int(tier["unit_price_tiyin"] or 0)
            if unit_price <= 0:
                raise ApiError(400, "INVALID_TIER_PRICE", "Tier narxi 0 tiyindan katta bo'lishi shart.")
            PriceTier.objects.create(
                offer=offer,
                min_qty=min_qty,
                max_qty=max_qty,
                unit_price_tiyin=unit_price,
            )

    return offer


def calculate_offer_price_for_qty(offer: Offer, quantity: int) -> tuple[int, int]:
    """
    Calculates (unit_price_tiyin, total_price_tiyin) for a given quantity using Tiered Pricing.
    All math is strict integer tiyin arithmetic.
    """
    if quantity < offer.min_order_qty:
        raise ApiError(
            400,
            "BELOW_MIN_ORDER_QTY",
            f"Minimal buyurtma miqdori: {offer.min_order_qty} dona. So'ralgan: {quantity}.",
        )

    unit_price_tiyin = offer.base_price_tiyin
    tiers = list(offer.price_tiers.all().order_by("min_qty"))
    for tier in tiers:
        if quantity >= tier.min_qty and (tier.max_qty is None or quantity <= tier.max_qty):
            unit_price_tiyin = tier.unit_price_tiyin

    total_price_tiyin = unit_price_tiyin * quantity
    return unit_price_tiyin, total_price_tiyin


def search_active_offers(query: Optional[str] = None, mxik_code: Optional[str] = None) -> List[Offer]:
    qs = Offer.objects.select_related("seller", "variant", "variant__product").prefetch_related("price_tiers").filter(
        is_active=True,
        variant__is_active=True,
    )
    if query:
        qs = qs.filter(
            Q(variant__name__icontains=query)
            | Q(variant__product__name__icontains=query)
            | Q(variant__barcode__icontains=query)
            | Q(variant__sku__icontains=query)
        )
    if mxik_code:
        qs = qs.filter(variant__mxik_code=mxik_code)
    return list(qs.order_by("base_price_tiyin")[:100])
