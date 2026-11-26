"""
Billing & FinTech Models:
- LedgerAccount (Organization balances & Data-for-Credit limits in BigIntegerField tiyin)
- DoubleEntryRecord (Immutable DEBIT / CREDIT paired journal entries in BigIntegerField tiyin)
- EscrowHold (Order/SubOrder escrow hold with unique idempotency_key and split settlement)
Zero FloatField allowed per GEMINI.md rule #3.
"""
from __future__ import annotations

import uuid
from django.core.validators import MinValueValidator
from django.db import models

from apps.iam.models import Organization
from apps.orders.models import Order, SubOrder


class AccountType(models.TextChoices):
    BUYER_WALLET = "BUYER_WALLET", "Xaridor hamyoni"
    SELLER_PAYABLE = "SELLER_PAYABLE", "Sotuvchi hisob-raqami"
    ESCROW_VAULT = "ESCROW_VAULT", "Escrow (Xavfsiz to'lov) seyfi"
    PLATFORM_REVENUE = "PLATFORM_REVENUE", "DBazar platforma komissiyasi"
    EXTERNAL_CLEARING = "EXTERNAL_CLEARING", "Payme / Click / Bank kliring hisobi"


class EntryType(models.TextChoices):
    DEBIT = "DEBIT", "Debit (-)"
    CREDIT = "CREDIT", "Credit (+)"


class EscrowStatus(models.TextChoices):
    HELD = "HELD", "Escrowda muzlatilgan"
    RELEASED = "RELEASED", "Sotuvchiga o'tkazilgan (Split Settlement)"
    REFUNDED = "REFUNDED", "Xaridorga qaytarilgan"


class LedgerAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ledger_accounts",
        help_text="Null for platform-level accounts (ESCROW_VAULT, PLATFORM_REVENUE, EXTERNAL_CLEARING)",
    )
    account_type = models.CharField(max_length=32, choices=AccountType.choices)
    currency = models.CharField(max_length=3, default="UZS")
    balance_tiyin = models.BigIntegerField(default=0)
    credit_limit_tiyin = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Data-for-Credit (B2B Nasiya) limiti (tiyinlarda)",
    )
    discount_tier_bps = models.PositiveIntegerField(
        default=0,
        help_text="VMI telemetriya uchun chegirma (basis points: 300 = 3%, 500 = 5%)",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_ledger_accounts"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "account_type", "currency"],
                name="uniq_ledger_org_type_currency",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "account_type"], name="idx_ledger_org_type"),
        ]

    def __str__(self) -> str:
        owner = self.organization.name if self.organization else "PLATFORM"
        return f"{owner} [{self.account_type}]: {self.balance_tiyin} tiyin"


class DoubleEntryRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_group_id = models.UUIDField(db_index=True)
    idempotency_key = models.CharField(max_length=128, db_index=True)
    account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    counterparty_account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name="counterparty_entries",
    )
    entry_type = models.CharField(max_length=12, choices=EntryType.choices)
    amount_tiyin = models.BigIntegerField(validators=[MinValueValidator(1)])
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_double_entry_records"
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key", "entry_type"],
                name="uniq_double_entry_idemp_type",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_tiyin__gt=0),
                name="chk_double_entry_amount_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["transaction_group_id"], name="idx_de_tx_group"),
            models.Index(fields=["account", "created_at"], name="idx_de_account_created"),
        ]

    @property
    def signed_amount_tiyin(self) -> int:
        return -self.amount_tiyin if self.entry_type == EntryType.DEBIT else self.amount_tiyin


class EscrowHold(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="escrow_holds",
    )
    sub_order = models.OneToOneField(
        SubOrder,
        on_delete=models.CASCADE,
        related_name="escrow_hold",
    )
    buyer_org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="buyer_escrows",
    )
    seller_org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="seller_escrows",
    )
    amount_tiyin = models.BigIntegerField(validators=[MinValueValidator(1)])
    seller_net_tiyin = models.BigIntegerField(default=0)
    platform_fee_tiyin = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=EscrowStatus.choices,
        default=EscrowStatus.HELD,
    )
    payment_provider = models.CharField(max_length=32, default="PAYME")
    idempotency_key = models.UUIDField(db_index=True)
    release_idempotency_key = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "billing_escrow_holds"
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key", "sub_order"],
                name="uniq_escrow_idemp_suborder",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_tiyin__gt=0),
                name="chk_escrow_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Escrow {self.id} [{self.status}] {self.amount_tiyin} tiyin"
