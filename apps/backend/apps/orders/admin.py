from django.contrib import admin
from apps.orders.models import Order, RfqBid, RfqTender, SubOrder, SubOrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer_org", "status", "total_amount_tiyin", "is_preorder", "created_at")
    list_filter = ("status", "is_preorder")


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "seller_org", "status", "subtotal_amount_tiyin", "waybill_qr_token", "is_pos_inbounded")
    list_filter = ("status", "is_pos_inbounded")


@admin.register(SubOrderItem)
class SubOrderItemAdmin(admin.ModelAdmin):
    list_display = ("sub_order", "variant", "batch_id", "quantity", "unit_price_tiyin", "line_total_tiyin")


@admin.register(RfqTender)
class RfqTenderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer_org", "variant", "target_quantity", "max_unit_price_tiyin", "region", "status", "created_at")
    list_filter = ("status", "region")


@admin.register(RfqBid)
class RfqBidAdmin(admin.ModelAdmin):
    list_display = ("id", "tender", "seller_org", "proposed_unit_price_tiyin", "is_winner", "created_at")
    list_filter = ("is_winner",)
