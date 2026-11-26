"""
Billing REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

from django.http import HttpRequest

from apps.billing.models import EscrowHold, LedgerAccount
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


def _serialize_account(acc: LedgerAccount) -> LedgerAccountResponse:
    return LedgerAccountResponse(
        id=acc.id,
        organization_id=acc.organization_id,
        account_type=acc.account_type,
        currency=acc.currency,
        balance_tiyin=acc.balance_tiyin,
        credit_limit_tiyin=acc.credit_limit_tiyin,
        discount_tier_bps=acc.discount_tier_bps,
    )


def _serialize_escrow(hold: EscrowHold) -> EscrowHoldResponse:
    return EscrowHoldResponse(
        id=hold.id,
        order_id=hold.order_id,
        sub_order_id=hold.sub_order_id,
        buyer_org_id=hold.buyer_org_id,
        seller_org_id=hold.seller_org_id,
        amount_tiyin=hold.amount_tiyin,
        seller_net_tiyin=hold.seller_net_tiyin,
        platform_fee_tiyin=hold.platform_fee_tiyin,
        status=hold.status,
        payment_provider=hold.payment_provider,
    )


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
    return _serialize_account(acc)


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
    return EscrowHoldListResponse(items=[_serialize_escrow(h) for h in holds])


@api_router.post(
    "billing/escrow/release",
    response=EscrowHoldResponse,
    status_code=200,
    tags=["Billing & Escrow"],
    summary="SubOrder topshirilgach Escrow mablag'ini Split Settlement orqali sotuvchiga o'tkazish",
    auth=True,
    operation_id="releaseSubOrderEscrow",
)
def release_escrow_endpoint(
    request: HttpRequest,
    payload: EscrowReleaseRequest,
) -> EscrowHoldResponse:
    user: User = request.user  # type: ignore[assignment]
    require_roles(
        user,
        [
            OrganizationRole.CUSTOMER,
            OrganizationRole.LOGISTICS,
            OrganizationRole.INTERMEDIARY,
            OrganizationRole.MANUFACTURER,
        ],
    )
    hold = release_escrow_split_settlement(
        sub_order_id=payload.sub_order_id,
        idempotency_key=payload.idempotency_key,
        platform_fee_bps=payload.platform_fee_bps,
    )
    return _serialize_escrow(hold)


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
    return _serialize_account(acc)
