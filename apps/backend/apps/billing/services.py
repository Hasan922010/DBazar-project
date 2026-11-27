"""
Billing Service Layer:
- Double-Entry Bookkeeping engine (DEBIT + CREDIT = 0 balance invariant)
- Atomic Escrow Hold with idempotency_key and select_for_update()
- Split Settlement on Delivery (Seller Net + Platform Fee = 100% of Escrow Hold, 0 tiyin drift)
- Phase 5 Data-for-Credit Scoring (calculates B2B credit limit & 3-5% discount tier from VMI telemetry)
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.billing.models import (
    AccountType,
    DoubleEntryRecord,
    EntryType,
    EscrowHold,
    EscrowStatus,
    LedgerAccount,
)
from apps.iam.models import Organization, OrganizationRole
from apps.inventory.models import InventoryLineage, PosTelemetryPermission
from apps.inventory.services import commit_reserved_seller_stock
from apps.orders.models import Order, OrderStatus, SubOrder
from config.api_router import ApiError

DEFAULT_PLATFORM_FEE_BPS = 100


def get_or_create_ledger_account(
    organization: Optional[Organization],
    account_type: str,
) -> LedgerAccount:
    acc = LedgerAccount.objects.filter(
        organization=organization,
        account_type=account_type,
        currency="UZS",
    ).first()
    if acc is not None:
        return acc
    try:
        with transaction.atomic():
            acc, _ = LedgerAccount.objects.get_or_create(
                organization=organization,
                account_type=account_type,
                currency="UZS",
                defaults={"balance_tiyin": 0, "credit_limit_tiyin": 0},
            )
            return acc
    except IntegrityError:
        return LedgerAccount.objects.get(
            organization=organization,
            account_type=account_type,
            currency="UZS",
        )


@transaction.atomic
def execute_double_entry_transfer(
    *,
    debit_account_id: uuid.UUID,
    credit_account_id: uuid.UUID,
    amount_tiyin: int,
    idempotency_key: str,
    description: str,
    allow_negative_debit: bool = False,
) -> uuid.UUID:
    """
    Executes an atomic Double-Entry transfer between two LedgerAccounts.
    Locks both accounts in deterministic UUID order using `select_for_update()`.
    Idempotent by `idempotency_key`.
    """
    if amount_tiyin <= 0:
        raise ApiError(400, "INVALID_AMOUNT", "O'tkazma summasi 0 tiyindan katta bo'lishi shart.")
    if debit_account_id == credit_account_id:
        raise ApiError(400, "SAME_ACCOUNT_TRANSFER", "Debit va Credit hisoblari bir xil bo'lishi mumkin emas.")

    existing = DoubleEntryRecord.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return existing.transaction_group_id

    # Lock accounts in deterministic order to avoid deadlocks
    ordered_ids = sorted([debit_account_id, credit_account_id], key=str)
    locked_map = {
        acc.id: acc
        for acc in LedgerAccount.objects.select_for_update().filter(id__in=ordered_ids)
    }
    debit_acc = locked_map[debit_account_id]
    credit_acc = locked_map[credit_account_id]

    available_funds = debit_acc.balance_tiyin + debit_acc.credit_limit_tiyin
    if not allow_negative_debit and available_funds < amount_tiyin:
        raise ApiError(
            402,
            "INSUFFICIENT_FUNDS",
            f"Hamyonda yetarli mablag' yo'q. Mavjud (nasiya limiti bilan): {available_funds} tiyin, kerak: {amount_tiyin} tiyin.",
        )

    debit_acc.balance_tiyin -= amount_tiyin
    credit_acc.balance_tiyin += amount_tiyin
    debit_acc.save(update_fields=["balance_tiyin", "updated_at"])
    credit_acc.save(update_fields=["balance_tiyin", "updated_at"])

    tx_group_id = uuid.uuid4()
    DoubleEntryRecord.objects.create(
        transaction_group_id=tx_group_id,
        idempotency_key=idempotency_key,
        account=debit_acc,
        counterparty_account=credit_acc,
        entry_type=EntryType.DEBIT,
        amount_tiyin=amount_tiyin,
        description=description,
    )
    DoubleEntryRecord.objects.create(
        transaction_group_id=tx_group_id,
        idempotency_key=idempotency_key,
        account=credit_acc,
        counterparty_account=debit_acc,
        entry_type=EntryType.CREDIT,
        amount_tiyin=amount_tiyin,
        description=description,
    )
    return tx_group_id


@transaction.atomic
def topup_buyer_wallet(
    *,
    organization: Organization,
    amount_tiyin: int,
    idempotency_key: uuid.UUID,
    provider: str = "PAYME",
) -> LedgerAccount:
    clearing_acc = get_or_create_ledger_account(None, AccountType.EXTERNAL_CLEARING)
    wallet_acc = get_or_create_ledger_account(organization, AccountType.BUYER_WALLET)

    execute_double_entry_transfer(
        debit_account_id=clearing_acc.id,
        credit_account_id=wallet_acc.id,
        amount_tiyin=amount_tiyin,
        idempotency_key=f"topup:{idempotency_key}",
        description=f"Wallet top-up via {provider}",
        allow_negative_debit=True,
    )
    wallet_acc.refresh_from_db()
    return wallet_acc


@transaction.atomic
def hold_order_payment_in_escrow(
    *,
    order_id: uuid.UUID,
    buyer_org: Organization,
    idempotency_key: uuid.UUID,
    payment_provider: str = "PAYME",
) -> List[EscrowHold]:
    """
    Atomically moves `Order.total_amount_tiyin` from Buyer's Wallet to Platform Escrow Vault
    and creates an `EscrowHold` record for each seller's `SubOrder`.
    Idempotent by `idempotency_key`.
    """
    existing_holds = list(
        EscrowHold.objects.select_related("sub_order", "seller_org")
        .filter(idempotency_key=idempotency_key)
    )
    if existing_holds:
        if existing_holds[0].order_id != order_id or existing_holds[0].buyer_org_id != buyer_org.id:
            raise ApiError(409, "IDEMPOTENCY_KEY_CONFLICT", "Idempotency kaliti boshqa to'lov uchun ishlatilgan.")
        return existing_holds

    order = (
        Order.objects.select_for_update()
        .prefetch_related("sub_orders__seller_org")
        .filter(id=order_id, buyer_org=buyer_org)
        .first()
    )
    if order is None:
        raise ApiError(404, "ORDER_NOT_FOUND", "Buyurtma topilmadi.")
    if order.status != OrderStatus.PENDING:
        raise ApiError(409, "ORDER_ALREADY_PROCESSED", f"Buyurtma holati: {order.status}")

    buyer_wallet = get_or_create_ledger_account(buyer_org, AccountType.BUYER_WALLET)
    escrow_vault = get_or_create_ledger_account(None, AccountType.ESCROW_VAULT)

    holds: List[EscrowHold] = []
    for sub_order in order.sub_orders.all():
        execute_double_entry_transfer(
            debit_account_id=buyer_wallet.id,
            credit_account_id=escrow_vault.id,
            amount_tiyin=sub_order.subtotal_amount_tiyin,
            idempotency_key=f"escrow-hold:{idempotency_key}:{sub_order.id}",
            description=f"Escrow hold for SubOrder {sub_order.id}",
        )
        hold = EscrowHold.objects.create(
            order=order,
            sub_order=sub_order,
            buyer_org=buyer_org,
            seller_org=sub_order.seller_org,
            amount_tiyin=sub_order.subtotal_amount_tiyin,
            status=EscrowStatus.HELD,
            payment_provider=payment_provider,
            idempotency_key=idempotency_key,
        )
        sub_order.status = OrderStatus.CONFIRMED
        sub_order.save(update_fields=["status", "updated_at"])
        holds.append(hold)

    order.status = OrderStatus.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    return holds


@transaction.atomic
def release_escrow_split_settlement(
    *,
    sub_order_id: uuid.UUID,
    idempotency_key: uuid.UUID,
    caller_org: Optional[Organization] = None,
    platform_fee_bps: int = DEFAULT_PLATFORM_FEE_BPS,
) -> EscrowHold:
    """
    Releases Escrow for a delivered SubOrder using Split Settlement:
    - `platform_fee_tiyin = (amount_tiyin * platform_fee_bps) // 10_000`
    - `seller_net_tiyin = amount_tiyin - platform_fee_tiyin`
    Invariant: `seller_net_tiyin + platform_fee_tiyin == amount_tiyin` (0 tiyin difference!).
    When called directly by a user (`caller_org` is provided), verifies buyer ownership.
    """
    existing_by_key = EscrowHold.objects.filter(release_idempotency_key=idempotency_key).first()
    if existing_by_key is not None:
        if existing_by_key.sub_order_id != sub_order_id:
            raise ApiError(409, "IDEMPOTENCY_KEY_CONFLICT", "Release idempotency kaliti boshqa SubOrder ga tegishli.")
        if caller_org is not None and caller_org.role != OrganizationRole.ADMIN and existing_by_key.buyer_org_id != caller_org.id:
            raise ApiError(403, "FORBIDDEN_ESCROW_RELEASE", "Faqat xaridor tashkilot Escrow to'lovini tasdiqlay oladi.")
        return existing_by_key

    sub_order = (
        SubOrder.objects.select_for_update()
        .select_related("order", "order__buyer_org", "seller_org")
        .prefetch_related("items")
        .filter(id=sub_order_id)
        .first()
    )
    if sub_order is None:
        raise ApiError(404, "SUBORDER_NOT_FOUND", "SubOrder topilmadi.")
    if caller_org is not None and caller_org.role != OrganizationRole.ADMIN and sub_order.order.buyer_org_id != caller_org.id:
        raise ApiError(403, "FORBIDDEN_ESCROW_RELEASE", "Faqat xaridor tashkilot Escrow to'lovini tasdiqlay oladi.")

    hold = EscrowHold.objects.select_for_update().filter(sub_order=sub_order).first()
    if hold is None:
        raise ApiError(404, "ESCROW_NOT_FOUND", "Ushbu SubOrder uchun Escrow to'lovi topilmadi.")
    if hold.status == EscrowStatus.RELEASED:
        return hold

    platform_fee_tiyin = (hold.amount_tiyin * platform_fee_bps) // 10_000
    seller_net_tiyin = hold.amount_tiyin - platform_fee_tiyin

    escrow_vault = get_or_create_ledger_account(None, AccountType.ESCROW_VAULT)
    seller_payable = get_or_create_ledger_account(sub_order.seller_org, AccountType.SELLER_PAYABLE)
    platform_revenue = get_or_create_ledger_account(None, AccountType.PLATFORM_REVENUE)

    if seller_net_tiyin > 0:
        execute_double_entry_transfer(
            debit_account_id=escrow_vault.id,
            credit_account_id=seller_payable.id,
            amount_tiyin=seller_net_tiyin,
            idempotency_key=f"escrow-release-seller:{idempotency_key}",
            description=f"Split settlement payout to seller for SubOrder {sub_order.id}",
        )

    if platform_fee_tiyin > 0:
        execute_double_entry_transfer(
            debit_account_id=escrow_vault.id,
            credit_account_id=platform_revenue.id,
            amount_tiyin=platform_fee_tiyin,
            idempotency_key=f"escrow-release-fee:{idempotency_key}",
            description=f"Platform commission for SubOrder {sub_order.id}",
        )

    hold.seller_net_tiyin = seller_net_tiyin
    hold.platform_fee_tiyin = platform_fee_tiyin
    hold.status = EscrowStatus.RELEASED
    hold.release_idempotency_key = idempotency_key
    hold.released_at = timezone.now()
    hold.save(
        update_fields=[
            "seller_net_tiyin",
            "platform_fee_tiyin",
            "status",
            "release_idempotency_key",
            "released_at",
        ]
    )

    sub_order.status = OrderStatus.DELIVERED
    sub_order.save(update_fields=["status", "updated_at"])

    for item in sub_order.items.all():
        commit_reserved_seller_stock(
            seller_org=sub_order.seller_org,
            variant_id=item.variant_id,
            batch_id=item.batch_id,
            qty=item.quantity,
        )

    # Check if all sub_orders of the parent order are delivered
    if not sub_order.order.sub_orders.exclude(status=OrderStatus.DELIVERED).exists():
        sub_order.order.status = OrderStatus.DELIVERED
        sub_order.order.save(update_fields=["status", "updated_at"])

    return hold


@transaction.atomic
def evaluate_data_for_credit_scoring(customer_org: Organization) -> LedgerAccount:
    """
    Phase 5 Data-for-Credit Module:
    If the store has active POS telemetry permissions, computes B2B Nasiya (credit limit)
    and 3%–5% discount tier (300–500 bps) based on POS sales volume & order history.
    """
    wallet = get_or_create_ledger_account(customer_org, AccountType.BUYER_WALLET)
    has_active_telemetry = PosTelemetryPermission.objects.filter(
        customer_org=customer_org,
        is_active=True,
    ).exists()

    if not has_active_telemetry:
        wallet.credit_limit_tiyin = 0
        wallet.discount_tier_bps = 0
        wallet.save(update_fields=["credit_limit_tiyin", "discount_tier_bps", "updated_at"])
        return wallet

    delivered_turnover_tiyin = (
        Order.objects.filter(buyer_org=customer_org, status=OrderStatus.DELIVERED)
        .aggregate(total=Sum("total_amount_tiyin"))
        .get("total")
        or 0
    )
    total_pos_sold_units = (
        InventoryLineage.objects.filter(customer_org=customer_org)
        .aggregate(total=Sum("sold_pos_qty"))
        .get("total")
        or 0
    )

    # Base credit limit = 50% of delivered B2B turnover + 100,000 UZS (10,000,000 tiyin) per 10 POS sold units
    computed_limit_tiyin = (delivered_turnover_tiyin // 2) + (total_pos_sold_units * 1_000_000)
    computed_limit_tiyin = max(computed_limit_tiyin, 500_000_000)  # Minimum 5,000,000 UZS credit line for VMI partners

    discount_bps = 500 if total_pos_sold_units >= 50 else 300

    wallet.credit_limit_tiyin = computed_limit_tiyin
    wallet.discount_tier_bps = discount_bps
    wallet.save(update_fields=["credit_limit_tiyin", "discount_tier_bps", "updated_at"])
    return wallet
