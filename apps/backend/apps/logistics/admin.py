from django.contrib import admin
from apps.logistics.models import Shipment, TrackingLog


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "sub_order", "logistics_org", "driver", "status", "pod_otp_code", "delivered_at")
    list_filter = ("status",)


@admin.register(TrackingLog)
class TrackingLogAdmin(admin.ModelAdmin):
    list_display = ("shipment", "lat_microdeg", "lng_microdeg", "recorded_at")
