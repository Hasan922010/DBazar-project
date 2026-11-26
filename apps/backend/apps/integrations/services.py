"""
Integrations Service Layer:
1. Didox / Faktura.uz EHF generation & E-Imzo PKCS#7 verification
2. Soliq.uz Virtual Kassa (OFD) fiscal receipt & QR generation (with 17-digit MXIK validation)
3. "DBazar Connect" External POS API (1C:Roznitsa, Billz, Regos, F-Apteka 1-Click Waybill & VMI Telemetry bridge)
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from django.db import transaction

from apps.iam.models import Organization
from apps.iam.services import UzGovSandboxEmulator
from apps.integrations.models import EhfDocument, OfdFiscalReceipt
from apps.orders.models import SubOrder
from apps.pos_sync.models import PosSale, PosStore
from apps.pos_sync.services import execute_one_click_waybill_inbound
from config.api_router import ApiError


@transaction.atomic
def generate_didox_ehf_for_suborder(
    *,
    seller_org: Organization,
    sub_order_id: uuid.UUID,
    pkcs7_signature: str,
) -> EhfDocument:
    sub_order = (
        SubOrder.objects.select_related("order__buyer_org", "seller_org")
        .filter(id=sub_order_id, seller_org=seller_org)
        .first()
    )
    if sub_order is None:
        raise ApiError(404, "SUBORDER_NOT_FOUND", "SubOrder topilmadi yoki sizning tashkilotingizga tegishli emas.")

    existing = EhfDocument.objects.filter(sub_order=sub_order).first()
    if existing is not None:
        return existing

    try:
        didox_data = UzGovSandboxEmulator.create_didox_ehf_document(
            sub_order_id=str(sub_order.id),
            seller_stir=seller_org.stir_inn,
            buyer_stir=sub_order.order.buyer_org.stir_inn,
            total_amount_tiyin=sub_order.subtotal_amount_tiyin,
            pkcs7_signature=pkcs7_signature,
        )
    except ValueError as exc:
        raise ApiError(400, "DIDOX_EHF_ERROR", str(exc)) from exc

    return EhfDocument.objects.create(
        sub_order=sub_order,
        didox_doc_id=didox_data["didox_doc_id"],
        seller_stir=didox_data["seller_stir"],
        buyer_stir=didox_data["buyer_stir"],
        total_amount_tiyin=didox_data["total_amount_tiyin"],
        certificate_serial=didox_data["certificate_serial"],
        status=didox_data["status"],
    )


@transaction.atomic
def register_pos_sale_with_soliq_ofd(
    *,
    customer_org: Organization,
    store_id: uuid.UUID,
    client_sale_id: uuid.UUID,
    receipt_seq: int,
    payment_method: str,
    total_amount_tiyin: int,
    mxik_codes: List[str],
    hlc_timestamp: str,
) -> OfdFiscalReceipt:
    existing_sale = PosSale.objects.select_related("ofd_receipt").filter(client_sale_id=client_sale_id).first()
    if existing_sale is not None and hasattr(existing_sale, "ofd_receipt"):
        return existing_sale.ofd_receipt

    store = PosStore.objects.filter(id=store_id, organization=customer_org, is_active=True).first()
    if store is None:
        raise ApiError(404, "POS_STORE_NOT_FOUND", "POS do'koni topilmadi.")

    try:
        ofd_data = UzGovSandboxEmulator.register_ofd_fiscal_receipt(
            terminal_id=store.terminal_id,
            receipt_seq=receipt_seq,
            total_amount_tiyin=total_amount_tiyin,
            mxik_codes=mxik_codes,
        )
    except ValueError as exc:
        raise ApiError(400, "SOLIQ_OFD_VALIDATION_ERROR", str(exc)) from exc

    sale = PosSale.objects.create(
        store=store,
        client_sale_id=client_sale_id,
        receipt_seq=receipt_seq,
        payment_method=payment_method,
        total_amount_tiyin=total_amount_tiyin,
        fiscal_sign=ofd_data["fiscal_sign"],
        fiscal_qr_url=ofd_data["qr_code_url"],
        hlc_timestamp=hlc_timestamp,
    )
    return OfdFiscalReceipt.objects.create(
        pos_sale=sale,
        terminal_id=store.terminal_id,
        receipt_seq=receipt_seq,
        total_amount_tiyin=total_amount_tiyin,
        fiscal_sign=ofd_data["fiscal_sign"],
        qr_code_url=ofd_data["qr_code_url"],
    )


@transaction.atomic
def dbazar_connect_external_pos_inbound(
    *,
    customer_org: Organization,
    external_system: str,
    terminal_id: str,
    waybill_qr_token: str,
) -> Dict[str, Any]:
    """
    "DBazar Connect" Open API for external POS systems (1C:Roznitsa, Billz, Regos, F-Apteka):
    Ensures a virtual PosStore exists for `terminal_id`, executes 1-Click Auto-Inbound,
    and returns the structured waybill items with 17-digit MXIK codes and tiyin prices.
    """
    store, _ = PosStore.objects.get_or_create(
        terminal_id=terminal_id,
        defaults={
            "organization": customer_org,
            "name": f"{customer_org.name} ({external_system} - {terminal_id})",
            "address": customer_org.address,
        },
    )
    if store.organization_id != customer_org.id:
        raise ApiError(403, "TERMINAL_ORG_MISMATCH", "Terminal boshqa tashkilotga biriktirilgan.")

    inbound_result = execute_one_click_waybill_inbound(
        customer_org=customer_org,
        store_id=store.id,
        waybill_qr_token=waybill_qr_token,
    )
    return {
        "external_system": external_system,
        "terminal_id": terminal_id,
        **inbound_result,
    }
