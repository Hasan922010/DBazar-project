"""
Catalog REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

import uuid
from typing import Optional
from django.http import HttpRequest

from apps.catalog.models import Offer, ProductVariant
from apps.catalog.schemas import (
    CalculatePriceRequest,
    CalculatePriceResponse,
    CreateProductVariantRequest,
    OfferListResponse,
    OfferResponse,
    PriceTierResponse,
    ProductVariantResponse,
    UpsertOfferRequest,
)
from apps.catalog.services import (
    calculate_offer_price_for_qty,
    create_product_with_variant,
    search_active_offers,
    upsert_offer_with_price_tiers,
)
from apps.iam.models import OrganizationRole, User
from apps.iam.services import require_roles
from config.api_router import ApiError, api_router


def _serialize_variant(variant: ProductVariant) -> ProductVariantResponse:
    return ProductVariantResponse(
        id=variant.id,
        product_id=variant.product_id,
        product_name=variant.product.name,
        brand=variant.product.brand,
        sku=variant.sku,
        variant_name=variant.name,
        mxik_code=variant.mxik_code,
        barcode=variant.barcode,
        unit_type=variant.unit_type,
        packaging_coefficient=variant.packaging_coefficient,
        weight_grams=variant.weight_grams,
    )


def _serialize_offer(offer: Offer) -> OfferResponse:
    return OfferResponse(
        id=offer.id,
        seller_id=offer.seller_id,
        seller_name=offer.seller.name,
        variant=_serialize_variant(offer.variant),
        base_price_tiyin=offer.base_price_tiyin,
        min_order_qty=offer.min_order_qty,
        price_tiers=[
            PriceTierResponse(
                min_qty=t.min_qty,
                max_qty=t.max_qty,
                unit_price_tiyin=t.unit_price_tiyin,
            )
            for t in offer.price_tiers.all()
        ],
    )


@api_router.post(
    "catalog/products",
    response=ProductVariantResponse,
    status_code=201,
    tags=["Catalog"],
    summary="17 xonali MXIK bilan yangi tovar va variant yaratish",
    auth=True,
    operation_id="createCatalogProductVariant",
)
def create_product_endpoint(
    request: HttpRequest,
    payload: CreateProductVariantRequest,
) -> ProductVariantResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(user, [OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY])
    _, variant = create_product_with_variant(
        manufacturer=org,
        name=payload.name,
        brand=payload.brand,
        description=payload.description,
        sku=payload.sku,
        variant_name=payload.variant_name,
        mxik_code=payload.mxik_code,
        barcode=payload.barcode,
        unit_type=payload.unit_type,
        packaging_coefficient=payload.packaging_coefficient,
        weight_grams=payload.weight_grams,
        category_slug=payload.category_slug,
    )
    return _serialize_variant(variant)


@api_router.post(
    "catalog/offers",
    response=OfferResponse,
    status_code=201,
    tags=["Catalog"],
    summary="Ulgurji narx va hajmga qarab narx pog'onalarini (Tiered Pricing) belgilash",
    auth=True,
    operation_id="upsertCatalogOffer",
)
def upsert_offer_endpoint(
    request: HttpRequest,
    payload: UpsertOfferRequest,
) -> OfferResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(user, [OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY])
    offer = upsert_offer_with_price_tiers(
        seller=org,
        variant_id=payload.variant_id,
        base_price_tiyin=payload.base_price_tiyin,
        min_order_qty=payload.min_order_qty,
        tiers=[t.model_dump() for t in payload.tiers],
    )
    return _serialize_offer(offer)


@api_router.get(
    "catalog/offers",
    response=OfferListResponse,
    status_code=200,
    tags=["Catalog"],
    summary="Tovarlarni qidirish va ulgurji narxlarni solishtirish",
    auth=False,
    operation_id="listCatalogOffers",
)
def list_offers_endpoint(
    request: HttpRequest,
    q: Optional[str] = None,
    mxik_code: Optional[str] = None,
) -> OfferListResponse:
    offers = search_active_offers(query=q, mxik_code=mxik_code)
    return OfferListResponse(items=[_serialize_offer(o) for o in offers])


@api_router.post(
    "catalog/offers/{offer_id}/calculate-price",
    response=CalculatePriceResponse,
    status_code=200,
    tags=["Catalog"],
    summary="Miqdorga qarab Tiered Pricing narxini (tiyinlarda) hisoblash",
    auth=False,
    operation_id="calculateOfferTieredPrice",
)
def calculate_price_endpoint(
    request: HttpRequest,
    offer_id: str,
    payload: CalculatePriceRequest,
) -> CalculatePriceResponse:
    offer = Offer.objects.prefetch_related("price_tiers").filter(id=uuid.UUID(offer_id), is_active=True).first()
    if offer is None:
        raise ApiError(404, "OFFER_NOT_FOUND", "Taklif topilmadi.")
    unit_price, total_price = calculate_offer_price_for_qty(offer, payload.quantity)
    return CalculatePriceResponse(
        offer_id=offer.id,
        quantity=payload.quantity,
        unit_price_tiyin=unit_price,
        total_price_tiyin=total_price,
    )
