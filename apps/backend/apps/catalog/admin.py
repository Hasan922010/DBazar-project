from django.contrib import admin
from apps.catalog.models import Category, Offer, PriceTier, Product, ProductVariant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "manufacturer", "is_active", "created_at")
    search_fields = ("name", "brand")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "mxik_code", "barcode", "unit_type", "packaging_coefficient")
    search_fields = ("sku", "name", "mxik_code", "barcode")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("seller", "variant", "base_price_tiyin", "min_order_qty", "is_active")


@admin.register(PriceTier)
class PriceTierAdmin(admin.ModelAdmin):
    list_display = ("offer", "min_qty", "max_qty", "unit_price_tiyin")
