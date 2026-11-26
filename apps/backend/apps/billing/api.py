"""
Billing REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

from django.http import HttpRequest

from apps.billing.schemas import (
    EscrowHoldListResponse,
    EscrowHoldRequest,
    EscrowHoldResponse,
    EscrowReleaseRequest,
    LedgerAccountResponse,
    WalletTopupRequest,
)
from apps.billing.services import (
    evaluate_data_for_credit_scoring,
    hold_order_payment_in_escrow,
    release_escrow_split_settlement,
    topup_buyer_wallet,
)
from apps.iam.models import OrganizationRole, User
from apps.iam.services import require_roles
from config.api_router import api_router


@api_router.post(
    "billing/wallet/topup",
    response=LedgerAccountResponse,
    status_code=200,
    tags=["Billing & Escrow"],
    summary="Xaridor hamyonini Payme/Click/Bank orqali to'ldirish (Double-Entry + Idempotent)",
    auth=True,
    operation_id="topupBuyerWallet",
)
def topup_wallet_endpoint(
    request: HttpRequest,
    payload: WalletTopupRequest,
) -> LedgerAccountResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(user, [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY])
    acc = topup_buyer_wallet(
        organization=org,
        amount_tiyin=payload.amount_tiyin,
        idempotency_key=payload.idempotency_key,
        provider=payload.provider,
    )
    return LedgerAccountResponse.model_validate(acc)


@api_router.post(
    "billing/escrow/hold",
    response=EscrowHoldListResponse,
    status_code=200,
    tags=["Billing & Escrow"],
    summary="Buyurtma to'lovini yetkazib berilgunga qadar Escrow hisobida muzlatish",
    auth=True,
    operation_id="holdOrderEscrow",
)
def hold_escrow_endpoint(
    request: HttpRequest,
    payload: EscrowHoldRequest,
) -> EscrowHoldListResponse:
    user: User = request.user  # type: ignore[assignment]
    buyer_org = require_roles(user, [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY])
    holds = hold_order_payment_in_escrow(
        order_id=payload.order_id,
        buyer_org=buyer_org,
        idempotency_key=payload.idempotency_key,
        payment_provider=payload.payment_provider,
    )
    return EscrowHoldListResponse(items=[EscrowHoldResponse.model_validate(h) for h in holds])


@api_router.post(
    "billing/escrow/release",
    response=EscrowHoldResponse,
    status_code=200,
    tags=["Billing & Escrow"],
    summary="SubOrder topshirilgach xaridor tomonidan Escrow mablag'ini Split Settlement orqali sotuvchiga o'tkazish",
    auth=True,
    operation_id="releaseSubOrderEscrow",
)
def release_escrow_endpoint(
    request: HttpRequest,
    payload: EscrowReleaseRequest,
) -> EscrowHoldResponse:
    user: User = request.user  # type: ignore[assignment]
    buyer_org = require_roles(user, [OrganizationRole.CUSTOMER, OrganizationRole.INTERMEDIARY])
    hold = release_escrow_split_settlement(
        sub_order_id=payload.sub_order_id,
        idempotency_key=payload.idempotency_key,
        caller_org=buyer_org,
    )
    return EscrowHoldResponse.model_validate(hold)


@api_router.post(
    "billing/credit-scoring/evaluate",
    response=LedgerAccountResponse,
    status_code=200,
    tags=["Billing & Escrow"],
    summary="Data-for-Credit: POS telemetriya asosida avtomatik B2B nasiya limiti va 3-5% chegirmani hisoblash",
    auth=True,
    operation_id="evaluateDataForCreditLimit",
)
def evaluate_credit_scoring_endpoint(request: HttpRequest) -> LedgerAccountResponse:
    user: User = request.user  # type: ignore[assignment]
    customer_org = require_roles(user, [OrganizationRole.CUSTOMER])
    acc = evaluate_data_for_credit_scoring(customer_org)
    return LedgerAccountResponse.model_validate(acc)
