from django.contrib import admin
from apps.integrations.models import EhfDocument, OfdFiscalReceipt


@admin.register(EhfDocument)
class EhfDocumentAdmin(admin.ModelAdmin):
    list_display = ("didox_doc_id", "sub_order", "seller_stir", "buyer_stir", "total_amount_tiyin", "status")


@admin.register(OfdFiscalReceipt)
class OfdFiscalReceiptAdmin(admin.ModelAdmin):
    list_display = ("terminal_id", "receipt_seq", "total_amount_tiyin", "fiscal_sign", "qr_code_url", "created_at")
