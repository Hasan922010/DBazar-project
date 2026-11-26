"""
IAM Service Layer: JWT Token issuance/verification, KYB E-Imzo verification, RBAC guards.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Iterable, Optional

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.http import HttpRequest

from apps.iam.models import KybStatus, Organization, OrganizationRole, User
from config.api_router import ApiError

# Import UzGovSandboxEmulator from packages/mocks-and-emulators/uz-gov-sandbox
SANDBOX_DIR = Path(settings.BASE_DIR).parent.parent / "packages" / "mocks-and-emulators" / "uz-gov-sandbox"
if str(SANDBOX_DIR) not in sys.path:
    sys.path.insert(0, str(SANDBOX_DIR))
from sandbox import UzGovSandboxEmulator  # type: ignore[import-not-found]  # noqa: E402


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_jwt_token(user: User, ttl_seconds: int = 86400) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "org_id": str(user.organization_id) if user.organization_id else None,
        "role": user.role,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def verify_jwt_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def resolve_request_user(request: HttpRequest) -> Optional[User]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer ") :].strip()
    claims = verify_jwt_token(token)
    if not claims or not claims.get("sub"):
        return None
    return User.objects.select_related("organization").filter(id=claims["sub"], is_active=True).first()


def require_roles(user: User, allowed_roles: Iterable[str]) -> Organization:
    allowed_set = set(allowed_roles)
    if user.role not in allowed_set and user.role != OrganizationRole.ADMIN:
        raise ApiError(
            403,
            "FORBIDDEN_ROLE",
            f"Ushbu amal uchun ruxsat etilgan rollar: {', '.join(sorted(allowed_set))}. Sizning rolingiz: {user.role}",
        )
    if user.organization is None:
        raise ApiError(403, "NO_ORGANIZATION", "Foydalanuvchi hech qanday tashkilotga biriktirilmagan.")
    return user.organization


@transaction.atomic
def register_organization_and_user(
    *,
    username: str,
    password: str,
    phone: str,
    org_name: str,
    legal_name: str,
    stir_inn: str,
    role: str,
    region: str = "Toshkent",
    address: str = "",
) -> tuple[Organization, User, str]:
    if Organization.objects.filter(stir_inn=stir_inn).exists():
        raise ApiError(409, "STIR_ALREADY_EXISTS", f"STIR {stir_inn} bilan tashkilot allaqachon ro'yxatdan o'tgan.")
    if User.objects.filter(username=username).exists() or User.objects.filter(phone=phone).exists():
        raise ApiError(409, "USER_ALREADY_EXISTS", "Foydalanuvchi nomi yoki telefon raqami band.")

    organization = Organization.objects.create(
        name=org_name,
        legal_name=legal_name,
        stir_inn=stir_inn,
        role=role,
        kyb_status=KybStatus.PENDING,
        region=region,
        address=address,
    )
    organization.full_clean()

    user = User(
        username=username,
        phone=phone,
        organization=organization,
        role=role,
    )
    user.set_password(password)
    user.save()

    token = issue_jwt_token(user)
    return organization, user, token


def authenticate_user_credentials(username: str, password: str) -> tuple[User, str]:
    user = authenticate(username=username, password=password)
    if user is None:
        raise ApiError(401, "INVALID_CREDENTIALS", "Login yoki parol noto'g'ri.")
    token = issue_jwt_token(user)
    return user, token


@transaction.atomic
def verify_organization_kyb_with_eimzo(
    *,
    organization_id: uuid.UUID,
    pkcs7_signature: str,
) -> Organization:
    org = Organization.objects.select_for_update().filter(id=organization_id).first()
    if org is None:
        raise ApiError(404, "ORG_NOT_FOUND", "Tashkilot topilmadi.")

    result = UzGovSandboxEmulator.verify_eimzo_pkcs7(pkcs7_signature, org.stir_inn)
    if not result["valid"]:
        org.kyb_status = KybStatus.REJECTED
        org.save(update_fields=["kyb_status", "updated_at"])
        raise ApiError(400, "EIMZO_VERIFICATION_FAILED", result["error"])

    org.kyb_status = KybStatus.VERIFIED
    org.eimzo_cert_serial = result["certificate_serial"]
    org.save(update_fields=["kyb_status", "eimzo_cert_serial", "updated_at"])
    return org
