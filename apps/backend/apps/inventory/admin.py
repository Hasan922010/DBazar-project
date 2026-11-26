from django.contrib import admin
from apps.inventory.models import (
    InventoryLineage,
    InventoryStock,
    PosTelemetryPermission,
    Warehouse,
)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "region", "is_active")


@admin.register(InventoryStock)
class InventoryStockAdmin(admin.ModelAdmin):
    list_display = ("warehouse", "variant", "batch_id", "available_qty", "reserved_qty", "expiry_date")


@admin.register(InventoryLineage)
class InventoryLineageAdmin(admin.ModelAdmin):
    list_display = (
        "customer_org",
        "variant",
        "batch_id",
        "intermediary_org",
        "manufacturer_org",
        "supplied_qty",
        "current_pos_qty",
        "sold_pos_qty",
    )


@admin.register(PosTelemetryPermission)
class PosTelemetryPermissionAdmin(admin.ModelAdmin):
    list_display = ("customer_org", "viewer_org", "variant", "batch_id", "is_active", "granted_at")
