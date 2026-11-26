"""
Integrations Models:
- EhfDocument (Didox / Faktura.uz Electronic Invoice signed with E-Imzo PKCS#7)
- OfdFiscalReceipt (Soliq.uz Virtual Kassa fiscal QR receipt with 72-hour offline queue support)
"""
from __future__ import annotations

import uuid
from django.core.validators import MinValueValidator
from django.db import models

from apps.orders.models import SubOrder
from apps.pos_sync.models import PosSale


class EhfDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.OneToOneField(
        SubOrder,
        on_delete=models.CASCADE,
        related_name="ehf_document",
    )
    didox_doc_id = models.CharField(max_length=64, unique=True)
    seller_stir = models.CharField(max_length=9)
    buyer_stir = models.CharField(max_length=9)
    total_amount_tiyin = models.BigIntegerField(validators=[MinValueValidator(1)])
    certificate_serial = models.CharField(max_length=128)
    status = models.CharField(max_length=32, default="SIGNED_BY_SELLER")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "integrations_ehf_documents"


class OfdFiscalReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pos_sale = models.OneToOneField(
        PosSale,
        on_delete=models.CASCADE,
        related_name="ofd_receipt",
    )
    terminal_id = models.CharField(max_length=64)
    receipt_seq = models.PositiveIntegerField()
    total_amount_tiyin = models.BigIntegerField(validators=[MinValueValidator(1)])
    fiscal_sign = models.CharField(max_length=64)
    qr_code_url = models.URLField()
    is_offline_queued = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "integrations_ofd_fiscal_receipts"
