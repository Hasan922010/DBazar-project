from django.contrib import admin
from apps.pos_sync.models import PosSale, PosShift, PosStockEvent, PosStore


@admin.register(PosStore)
class PosStoreAdmin(admin.ModelAdmin):
    list_display = ("name", "terminal_id", "organization", "last_hlc_timestamp", "is_active")


@admin.register(PosShift)
class PosShiftAdmin(admin.ModelAdmin):
    list_display = ("store", "cashier", "opening_cash_tiyin", "closing_cash_tiyin", "is_open", "opened_at")


@admin.register(PosSale)
class PosSaleAdmin(admin.ModelAdmin):
    list_display = ("store", "receipt_seq", "payment_method", "total_amount_tiyin", "fiscal_sign", "hlc_timestamp")


@admin.register(PosStockEvent)
class PosStockEventAdmin(admin.ModelAdmin):
    list_display = ("store", "event_type", "variant", "batch_id", "qty_delta", "hlc_timestamp", "client_event_id")
    list_filter = ("event_type",)
