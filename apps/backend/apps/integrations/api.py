"""
Integrations REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

from django.http import HttpRequest

from apps.iam.models import OrganizationRole, User
from apps.iam.services import require_roles
from apps.integrations.schemas import (
    DbazarConnectInboundRequest,
    DbazarConnectInboundResponse,
    EhfDocumentResponse,
    GenerateDidoxEhfRequest,
    OfdFiscalReceiptResponse,
    RegisterOfdReceiptRequest,
)
from apps.integrations.services import (
    dbazar_connect_external_pos_inbound,
    generate_didox_ehf_for_suborder,
    register_pos_sale_with_soliq_ofd,
)
from config.api_router import api_router


@api_router.post(
    "integrations/didox/ehf",
    response=EhfDocumentResponse,
    status_code=201,
    tags=["Integrations (Soliq & Didox)"],
    summary="SubOrder uchun Didox elektron hisobvaraq-faktura (EHF) yaratish va E-Imzo PKCS#7 ni tekshirish",
    auth=True,
    operation_id="generateDidoxEhfDocument",
)
def generate_ehf_endpoint(
    request: HttpRequest,
    payload: GenerateDidoxEhfRequest,
) -> EhfDocumentResponse:
    user: User = request.user  # type: ignore[assignment]
    seller_org = require_roles(user, [OrganizationRole.MANUFACTURER, OrganizationRole.INTERMEDIARY])
    doc = generate_didox_ehf_for_suborder(
        seller_org=seller_org,
        sub_order_id=payload.sub_order_id,
        pkcs7_signature=payload.pkcs7_signature,
    )
    return EhfDocumentResponse.model_validate(doc)


@api_router.post(
    "integrations/soliq/ofd-receipt",
    response=OfdFiscalReceiptResponse,
    status_code=201,
    tags=["Integrations (Soliq & Didox)"],
    summary="Soliq.uz Virtual Kassa (OFD) orqali POS chekiga fiskal belgi va QR-kod olish",
    auth=True,
    operation_id="registerSoliqOfdFiscalReceipt",
)
def register_ofd_receipt_endpoint(
    request: HttpRequest,
    payload: RegisterOfdReceiptRequest,
) -> OfdFiscalReceiptResponse:
    user: User = request.user  # type: ignore[assignment]
    customer_org = require_roles(user, [OrganizationRole.CUSTOMER])
    receipt = register_pos_sale_with_soliq_ofd(
        customer_org=customer_org,
        store_id=payload.store_id,
        client_sale_id=payload.client_sale_id,
        receipt_seq=payload.receipt_seq,
        payment_method=payload.payment_method,
        total_amount_tiyin=payload.total_amount_tiyin,
        mxik_codes=payload.mxik_codes,
        hlc_timestamp=payload.hlc_timestamp,
    )
    return OfdFiscalReceiptResponse.model_validate(receipt)


@api_router.post(
    "integrations/dbazar-connect/inbound",
    response=DbazarConnectInboundResponse,
    status_code=200,
    tags=["Integrations (DBazar Connect)"],
    summary="DBazar Connect: 1C:Roznitsa, Billz, Regos va F-Apteka kassalaridan 1-Click Avto-Kirim qilish",
    auth=True,
    operation_id="dbazarConnectExternalInbound",
)
def dbazar_connect_inbound_endpoint(
    request: HttpRequest,
    payload: DbazarConnectInboundRequest,
) -> DbazarConnectInboundResponse:
    user: User = request.user  # type: ignore[assignment]
    customer_org = require_roles(user, [OrganizationRole.CUSTOMER])
    result = dbazar_connect_external_pos_inbound(
        customer_org=customer_org,
        external_system=payload.external_system,
        terminal_id=payload.terminal_id,
        waybill_qr_token=payload.waybill_qr_token,
    )
    return DbazarConnectInboundResponse(**result)
