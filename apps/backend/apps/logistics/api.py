"""
Logistics REST Endpoints registered on the Contract-First API Router.
"""
from __future__ import annotations

import uuid
from django.http import HttpRequest

from apps.iam.models import OrganizationRole, User
from apps.iam.services import require_roles
from apps.logistics.schemas import (
    AssignShipmentRequest,
    ConfirmPodRequest,
    ShipmentResponse,
    UpdateShipmentGpsRequest,
)
from apps.logistics.services import (
    confirm_shipment_pod_and_release_escrow,
    create_or_assign_shipment,
    update_shipment_gps_and_status,
)
from config.api_router import api_router


@api_router.post(
    "logistics/shipments",
    response=ShipmentResponse,
    status_code=201,
    tags=["Logistics & POD"],
    summary="SubOrder uchun yetkazib berish (Shipment) yaratish va xaridorga maxfiy OTP kod shakllantirish",
    auth=True,
    operation_id="createOrAssignShipment",
)
def assign_shipment_endpoint(
    request: HttpRequest,
    payload: AssignShipmentRequest,
) -> ShipmentResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(
        user,
        [OrganizationRole.LOGISTICS, OrganizationRole.INTERMEDIARY, OrganizationRole.MANUFACTURER],
    )
    shipment = create_or_assign_shipment(
        sub_order_id=payload.sub_order_id,
        logistics_org=org,
        driver=user,
    )
    return ShipmentResponse.model_validate(shipment)


@api_router.post(
    "logistics/shipments/{shipment_id}/gps",
    response=ShipmentResponse,
    status_code=200,
    tags=["Logistics & POD"],
    summary="Haydovchi GPS koordinatasi va holatini yangilash (Ombordan oldim -> Yo'lga chiqdim)",
    auth=True,
    operation_id="updateShipmentGpsAndStatus",
)
def update_gps_endpoint(
    request: HttpRequest,
    shipment_id: str,
    payload: UpdateShipmentGpsRequest,
) -> ShipmentResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(
        user,
        [OrganizationRole.LOGISTICS, OrganizationRole.INTERMEDIARY, OrganizationRole.MANUFACTURER],
    )
    shipment = update_shipment_gps_and_status(
        shipment_id=uuid.UUID(shipment_id),
        caller_org=org,
        lat_microdeg=payload.lat_microdeg,
        lng_microdeg=payload.lng_microdeg,
        new_status=payload.status,
    )
    return ShipmentResponse.model_validate(shipment)


@api_router.post(
    "logistics/shipments/{shipment_id}/pod",
    response=ShipmentResponse,
    status_code=200,
    tags=["Logistics & POD"],
    summary="Topshirdim (POD): Xaridorning OTP kodi orqali yuk topshirilganini tasdiqlash va Escrow to'lovini yechish",
    auth=True,
    operation_id="confirmShipmentProofOfDelivery",
)
def confirm_pod_endpoint(
    request: HttpRequest,
    shipment_id: str,
    payload: ConfirmPodRequest,
) -> ShipmentResponse:
    user: User = request.user  # type: ignore[assignment]
    org = require_roles(
        user,
        [
            OrganizationRole.LOGISTICS,
            OrganizationRole.CUSTOMER,
            OrganizationRole.INTERMEDIARY,
            OrganizationRole.MANUFACTURER,
        ],
    )
    shipment = confirm_shipment_pod_and_release_escrow(
        shipment_id=uuid.UUID(shipment_id),
        caller_org=org,
        pod_otp_code=payload.pod_otp_code,
        release_idempotency_key=payload.release_idempotency_key,
        pod_photo_url=payload.pod_photo_url,
    )
    return ShipmentResponse.model_validate(shipment)
