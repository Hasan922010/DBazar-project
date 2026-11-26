"""
IAM Models: Organization (STIR/INN, KYB status, RBAC role) and Custom User.
"""
from __future__ import annotations

import uuid
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

stir_validator = RegexValidator(
    regex=r"^\d{9}$",
    message="STIR (INN) qat'iy 9 ta raqamdan iborat bo'lishi shart.",
)


class OrganizationRole(models.TextChoices):
    MANUFACTURER = "MANUFACTURER", "Ishlab chiqaruvchi"
    INTERMEDIARY = "INTERMEDIARY", "Vositachi (Distribyutor)"
    LOGISTICS = "LOGISTICS", "Logistika / Yetkazib berish"
    CUSTOMER = "CUSTOMER", "B2B Xaridor (Do'kon / POS)"
    ADMIN = "ADMIN", "Platforma Administratori"


class KybStatus(models.TextChoices):
    PENDING = "PENDING", "Tekshiruv kutilmoqda"
    VERIFIED = "VERIFIED", "E-Imzo / OneID orqali tasdiqlangan"
    REJECTED = "REJECTED", "Rad etilgan"
    SUSPENDED = "SUSPENDED", "Vaqtincha muzlatilgan"


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255)
    stir_inn = models.CharField(max_length=9, unique=True, validators=[stir_validator])
    role = models.CharField(max_length=32, choices=OrganizationRole.choices)
    kyb_status = models.CharField(
        max_length=24,
        choices=KybStatus.choices,
        default=KybStatus.PENDING,
    )
    eimzo_cert_serial = models.CharField(max_length=128, blank=True, default="")
    region = models.CharField(max_length=100, default="Toshkent")
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iam_organizations"
        indexes = [
            models.Index(fields=["role", "kyb_status"], name="idx_org_role_kyb"),
            models.Index(fields=["stir_inn"], name="idx_org_stir"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.stir_inn} - {self.role})"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(
        max_length=32,
        choices=OrganizationRole.choices,
        default=OrganizationRole.CUSTOMER,
    )
    is_2fa_enabled = models.BooleanField(default=False)
    two_fa_secret = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iam_users"
        indexes = [
            models.Index(fields=["organization", "role"], name="idx_user_org_role"),
            models.Index(fields=["phone"], name="idx_user_phone"),
        ]

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
