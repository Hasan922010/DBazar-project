from django.contrib import admin
from apps.billing.models import DoubleEntryRecord, EscrowHold, LedgerAccount


@admin.register(LedgerAccount)
class LedgerAccountAdmin(admin.ModelAdmin):
    list_display = ("organization", "account_type", "balance_tiyin", "credit_limit_tiyin", "discount_tier_bps")
    list_filter = ("account_type",)


@admin.register(DoubleEntryRecord)
class DoubleEntryRecordAdmin(admin.ModelAdmin):
    list_display = ("transaction_group_id", "account", "entry_type", "amount_tiyin", "idempotency_key", "created_at")
    list_filter = ("entry_type",)


@admin.register(EscrowHold)
class EscrowHoldAdmin(admin.ModelAdmin):
    list_display = ("id", "sub_order", "buyer_org", "seller_org", "amount_tiyin", "seller_net_tiyin", "platform_fee_tiyin", "status")
    list_filter = ("status", "payment_provider")
