"""
IAM REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

from django.http import HttpRequest

from apps.iam.models import Organization, User
from apps.iam.schemas import (
    AuthTokenResponse,
    KybVerifyRequest,
    LoginRequest,
    OrganizationResponse,
    RegisterOrganizationRequest,
    UserProfileResponse,
)
from apps.iam.services import (
    authenticate_user_credentials,
    register_organization_and_user,
    verify_organization_kyb_with_eimzo,
)
from config.api_router import ApiError, api_router


def _serialize_org(org: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        legal_name=org.legal_name,
        stir_inn=org.stir_inn,
        role=org.role,
        kyb_status=org.kyb_status,
        eimzo_cert_serial=org.eimzo_cert_serial,
        region=org.region,
    )


def _serialize_user(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        phone=user.phone,
        role=user.role,
        is_2fa_enabled=user.is_2fa_enabled,
        organization=_serialize_org(user.organization) if user.organization else None,
    )


@api_router.post(
    "iam/register",
    response=AuthTokenResponse,
    status_code=201,
    tags=["IAM"],
    summary="Tashkilot va foydalanuvchini ro'yxatdan o'tkazish",
    auth=False,
    operation_id="registerOrganizationAndUser",
)
def register_endpoint(request: HttpRequest, payload: RegisterOrganizationRequest) -> AuthTokenResponse:
    org, user, token = register_organization_and_user(
        username=payload.username,
        password=payload.password,
        phone=payload.phone,
        org_name=payload.org_name,
        legal_name=payload.legal_name,
        stir_inn=payload.stir_inn,
        role=payload.role,
        region=payload.region,
        address=payload.address,
    )
    user.organization = org
    return AuthTokenResponse(access_token=token, user=_serialize_user(user))


@api_router.post(
    "iam/login",
    response=AuthTokenResponse,
    status_code=200,
    tags=["IAM"],
    summary="Tizimga kirish va JWT token olish",
    auth=False,
    operation_id="loginUser",
)
def login_endpoint(request: HttpRequest, payload: LoginRequest) -> AuthTokenResponse:
    user, token = authenticate_user_credentials(payload.username, payload.password)
    return AuthTokenResponse(access_token=token, user=_serialize_user(user))


@api_router.post(
    "iam/kyb/verify",
    response=OrganizationResponse,
    status_code=200,
    tags=["IAM"],
    summary="E-Imzo PKCS#7 orqali tashkilot KYB maqomini tasdiqlash",
    auth=True,
    operation_id="verifyOrganizationKyb",
)
def verify_kyb_endpoint(request: HttpRequest, payload: KybVerifyRequest) -> OrganizationResponse:
    user: User = request.user  # type: ignore[assignment]
    if not user.organization_id:
        raise ApiError(400, "NO_ORGANIZATION", "Foydalanuvchi tashkilotga biriktirilmagan.")
    org = verify_organization_kyb_with_eimzo(
        organization_id=user.organization_id,
        pkcs7_signature=payload.pkcs7_signature,
    )
    return _serialize_org(org)


@api_router.get(
    "iam/me",
    response=UserProfileResponse,
    status_code=200,
    tags=["IAM"],
    summary="Joriy foydalanuvchi va tashkilot profili",
    auth=True,
    operation_id="getCurrentUserProfile",
)
def me_endpoint(request: HttpRequest) -> UserProfileResponse:
    user: User = request.user  # type: ignore[assignment]
    return _serialize_user(user)
