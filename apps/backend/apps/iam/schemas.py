"""
Pydantic v2 Contracts for IAM module.
"""
from __future__ import annotations

import uuid
from typing import Literal, Optional
from pydantic import BaseModel, Field


class RegisterOrganizationRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    phone: str = Field(..., min_length=9, max_length=20)
    org_name: str = Field(..., min_length=2, max_length=255)
    legal_name: str = Field(..., min_length=2, max_length=255)
    stir_inn: str = Field(..., pattern=r"^\d{9}$", description="9 xonali STIR (INN)")
    role: Literal["MANUFACTURER", "INTERMEDIARY", "LOGISTICS", "CUSTOMER", "ADMIN"]
    region: str = "Toshkent"
    address: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class KybVerifyRequest(BaseModel):
    pkcs7_signature: str = Field(..., min_length=12, description="E-Imzo PKCS#7 raqamli imzosi")


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    legal_name: str
    stir_inn: str
    role: str
    kyb_status: str
    eimzo_cert_serial: str
    region: str


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    username: str
    phone: str
    role: str
    is_2fa_enabled: bool
    organization: Optional[OrganizationResponse] = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserProfileResponse
