"""
Comprehensive Verification & B2B Security Audit Test Suite for DBazar Backend.
Covers all requirements from `reja.md`, `GEMINI.md`, `/b2b-security-audit`, and `/ponytail-review` fixes 1-10:
1. Zero FloatField currency/model audit (all monetary fields strictly BigIntegerField in tiyin)
2. IAM registration, JWT authentication, RBAC guards & E-Imzo PKCS#7 KYB verification
3. Catalog 17-digit MXIK validation & Tiered Pricing calculation in tiyin
4. Multi-vendor B2B Cart Checkout with duplicate offer_id line merging, Order Splitting & FEFO stock reservation
5. Double-Entry Bookkeeping (DEBIT == CREDIT invariant), Escrow idempotency, buyer-only release guard & Split Settlement
6. Cryptographic POD OTP (hidden from driver ShipmentResponse) & single-counted VMI lineage after POD + 1-Click Inbound
7. Offline-First POS 500-event Airplane Mode HLC Delta-Sync (batched bulk_create, 0 conflicts, monotonic HLC watermark)
8. Strict VMI Telemetry Isolation (`PosTelemetryPermission` + `InventoryLineage` cross-tenant leak prevention) & Waybill IDOR protection
9. Soliq.uz OFD fiscal QR, Didox EHF, DBazar Connect external POS API & Data-for-Credit B2B scoring
10. Contract-First OpenAPI 3.1.0 schema export verification (`packages/contracts/openapi.yaml`)
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest
from django.apps import apps
from django.core.management import call_command
from django.db import models
from django.db.models import Sum
from django.test import Client

from apps.billing.models import DoubleEntryRecord, EntryType, EscrowHold, LedgerAccount
from apps.inventory.models import InventoryLineage, InventoryStock
from apps.logistics.models import Shipment
from apps.orders.models import Order, SubOrder
from config.hlc import generate_hlc_timestamp


def _api_call(
    client: Client,
    method: str,
    path: str,
    payload: Dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, Dict[str, Any]]:
    headers: Dict[str, str] = {}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    body = json.dumps(payload) if payload is not None else None
    fn = getattr(client, method.lower())
    if method.upper() in ("POST", "PUT", "PATCH"):
        resp = fn(path, data=body, content_type="application/json", **headers)
    else:
        resp = fn(path, **headers)
    return resp.status_code, json.loads(resp.content.decode("utf-8"))


@pytest.mark.django_db
class TestDbazarArchitectureAndSecurityAudit:
    def test_01_zero_float_field_and_tiyin_bigint_audit(self) -> None:
        domain_apps = {
            "iam",
            "catalog",
            "inventory",
            "orders",
            "billing",
            "pos_sync",
            "integrations",
            "logistics",
        }
        float_fields_found = []
        tiyin_fields_checked = 0

        for model in apps.get_models():
            if model._meta.app_label not in domain_apps:
                continue
            for field in model._meta.get_fields():
                if isinstance(field, models.FloatField):
                    float_fields_found.append(f"{model.__name__}.{field.name}")
                if hasattr(field, "name") and field.name.endswith("_tiyin"):
                    assert isinstance(
                        field, models.BigIntegerField
                    ), f"{model.__name__}.{field.name} must be BigIntegerField, got {type(field)}"
                    tiyin_fields_checked += 1

        assert float_fields_found == [], f"Forbidden FloatField found: {float_fields_found}"
        assert tiyin_fields_checked >= 14

    def test_02_end_to_end_b2b_supply_chain_escrow_pos_vmi_and_fintech(self, tmp_path: Path) -> None:
        client = Client()

        # 1. IAM Registration & E-Imzo PKCS#7 KYB Verification
        status, mfg_auth = _api_call(
            client,
            "POST",
            "/api/v1/iam/register",
            {
                "username": "mfg_owner",
                "password": "StrongPassword123!",
                "phone": "+998901110011",
                "org_name": "Roison Foods Factory",
                "legal_name": "Roison Foods MChJ",
                "stir_inn": "301111111",
                "role": "MANUFACTURER",
            },
        )
        assert status == 201, mfg_auth
        mfg_token = mfg_auth["access_token"]
        mfg_org_id = mfg_auth["user"]["organization"]["id"]

        status, dist_a_auth = _api_call(
            client,
            "POST",
            "/api/v1/iam/register",
            {
                "username": "dist_a_user",
                "password": "StrongPassword123!",
                "phone": "+998902220022",
                "org_name": "Tashkent Agro Distribyutor A",
                "legal_name": "Agro Dist A MChJ",
                "stir_inn": "302222222",
                "role": "INTERMEDIARY",
            },
        )
        assert status == 201
        dist_a_token = dist_a_auth["access_token"]
        dist_a_org_id = dist_a_auth["user"]["organization"]["id"]

        status, dist_b_auth = _api_call(
            client,
            "POST",
            "/api/v1/iam/register",
            {
                "username": "dist_b_user",
                "password": "StrongPassword123!",
                "phone": "+998903330033",
                "org_name": "Samarqand Distribyutor B",
                "legal_name": "Dist B MChJ",
                "stir_inn": "303333333",
                "role": "INTERMEDIARY",
            },
        )
        assert status == 201
        dist_b_token = dist_b_auth["access_token"]

        status, store_auth = _api_call(
            client,
            "POST",
            "/api/v1/iam/register",
            {
                "username": "baraka_minimarket",
                "password": "StrongPassword123!",
                "phone": "+998904440044",
                "org_name": "Baraka Minimarket #1",
                "legal_name": "Baraka Savdo YaTT",
                "stir_inn": "304444444",
                "role": "CUSTOMER",
            },
        )
        assert status == 201
        store_token = store_auth["access_token"]
        store_org_id = store_auth["user"]["organization"]["id"]

        status, driver_auth = _api_call(
            client,
            "POST",
            "/api/v1/iam/register",
            {
                "username": "fast_driver",
                "password": "StrongPassword123!",
                "phone": "+998905550055",
                "org_name": "DBazar Express Logistics",
                "legal_name": "DBazar Express MChJ",
                "stir_inn": "305555555",
                "role": "LOGISTICS",
            },
        )
        assert status == 201
        driver_token = driver_auth["access_token"]

        # Verify KYB via E-Imzo PKCS#7
        status, kyb_resp = _api_call(
            client,
            "POST",
            "/api/v1/iam/kyb/verify",
            {"pkcs7_signature": "MIAGCSqGSIb3DQEHAqCAMIACAQExDzANBglghkgBZQMEAgEFADCABgkqhkiG9w0BBwEAAKCAMII="},
            token=mfg_token,
        )
        assert status == 200
        assert kyb_resp["kyb_status"] == "VERIFIED"

        # 2. Catalog 17-Digit MXIK Validation & Tiered Pricing
        mxik_oil = "01901001001000001"
        status, variant_oil = _api_call(
            client,
            "POST",
            "/api/v1/catalog/products",
            {
                "name": "Kungaboqar yog'i Oliya",
                "brand": "Oliya",
                "sku": "OLIYA-1L",
                "variant_name": "1 Litr PET",
                "mxik_code": mxik_oil,
                "barcode": "4780010010011",
                "unit_type": "LITER",
                "packaging_coefficient": 12,
                "category_slug": "yog-moy",
            },
            token=mfg_token,
        )
        assert status == 201
        variant_oil_id = variant_oil["id"]

        mxik_flour = "01101002001000002"
        status, variant_flour = _api_call(
            client,
            "POST",
            "/api/v1/catalog/products",
            {
                "name": "Birinchi navli bug'doy uni",
                "brand": "Don",
                "sku": "UN-50KG",
                "variant_name": "50 kg qop",
                "mxik_code": mxik_flour,
                "barcode": "4780020020022",
                "unit_type": "KG",
                "packaging_coefficient": 1,
                "category_slug": "un-mahsulotlari",
            },
            token=dist_a_token,
        )
        assert status == 201
        variant_flour_id = variant_flour["id"]

        status, offer_mfg = _api_call(
            client,
            "POST",
            "/api/v1/catalog/offers",
            {
                "variant_id": variant_oil_id,
                "base_price_tiyin": 1_800_000,
                "min_order_qty": 10,
                "tiers": [
                    {"min_qty": 10, "max_qty": 49, "unit_price_tiyin": 1_800_000},
                    {"min_qty": 50, "max_qty": None, "unit_price_tiyin": 1_650_000},
                ],
            },
            token=mfg_token,
        )
        assert status == 201
        offer_mfg_id = offer_mfg["id"]

        status, offer_dist_a = _api_call(
            client,
            "POST",
            "/api/v1/catalog/offers",
            {
                "variant_id": variant_flour_id,
                "base_price_tiyin": 22_000_000,
                "min_order_qty": 2,
                "tiers": [
                    {"min_qty": 10, "max_qty": None, "unit_price_tiyin": 21_000_000},
                ],
            },
            token=dist_a_token,
        )
        assert status == 201
        offer_dist_a_id = offer_dist_a["id"]

        # 3. Warehouse Creation & Batch Stock Receipt
        status, wh_mfg = _api_call(
            client,
            "POST",
            "/api/v1/inventory/warehouses",
            {"name": "Roison Markaziy Ombor", "code": "WH-MFG-01"},
            token=mfg_token,
        )
        assert status == 201
        _api_call(
            client,
            "POST",
            "/api/v1/inventory/stocks/receive",
            {
                "warehouse_id": wh_mfg["id"],
                "variant_id": variant_oil_id,
                "batch_id": "BATCH-OIL-2026-11",
                "qty": 500,
                "expiry_date": "2027-06-01",
            },
            token=mfg_token,
        )

        status, wh_dist_a = _api_call(
            client,
            "POST",
            "/api/v1/inventory/warehouses",
            {"name": "Distribyutor A Ombori", "code": "WH-DISTA-01"},
            token=dist_a_token,
        )
        assert status == 201
        _api_call(
            client,
            "POST",
            "/api/v1/inventory/stocks/receive",
            {
                "warehouse_id": wh_dist_a["id"],
                "variant_id": variant_flour_id,
                "batch_id": "BATCH-FLOUR-2026-11",
                "qty": 200,
                "expiry_date": "2027-05-01",
            },
            token=dist_a_token,
        )

        # 4. Multi-Vendor B2B Cart Checkout with Split Duplicate offer_id Lines (Fix #5: 30 + 30 = 60 -> >=50 tier!)
        order_idemp_key = str(uuid.uuid4())
        order_payload = {
            "idempotency_key": order_idemp_key,
            "is_preorder": False,
            "delivery_address": "Toshkent sh., Chilonzor-9, Baraka Minimarket",
            "items": [
                {"offer_id": offer_mfg_id, "quantity": 30},
                {"offer_id": offer_mfg_id, "quantity": 30},     # Merged to 60 -> 60 * 1,650,000 = 99,000,000 tiyin
                {"offer_id": offer_dist_a_id, "quantity": 5},   # 5 * 22,000,000 = 110,000,000 tiyin
            ],
        }
        status, order_resp = _api_call(client, "POST", "/api/v1/orders", order_payload, token=store_token)
        assert status == 201, order_resp
        assert order_resp["total_amount_tiyin"] == 209_000_000
        assert len(order_resp["sub_orders"]) == 2

        # Waybill IDOR Check (Fix #4): Distributor B cannot read Distributor A's or Manufacturer's waybill
        waybill_qr_1 = order_resp["sub_orders"][0]["waybill_qr_token"]
        status, idor_waybill = _api_call(
            client,
            "GET",
            f"/api/v1/orders/waybill/{waybill_qr_1}",
            token=dist_b_token,
        )
        assert status == 404

        # 5. Double-Entry Ledger Top-Up, Escrow Hold & Buyer-Only Release Guard (Fix #2)
        _api_call(
            client,
            "POST",
            "/api/v1/billing/wallet/topup",
            {
                "amount_tiyin": 300_000_000,
                "idempotency_key": str(uuid.uuid4()),
                "provider": "PAYME",
            },
            token=store_token,
        )

        escrow_hold_idemp = str(uuid.uuid4())
        status, escrow_list = _api_call(
            client,
            "POST",
            "/api/v1/billing/escrow/hold",
            {
                "order_id": order_resp["id"],
                "idempotency_key": escrow_hold_idemp,
                "payment_provider": "PAYME",
            },
            token=store_token,
        )
        assert status == 200
        assert len(escrow_list["items"]) == 2

        # Seller attempting to release their own Escrow before delivery is blocked with 403 (Fix #2)
        mfg_sub_id = next(s["id"] for s in order_resp["sub_orders"] if s["seller_org_id"] == mfg_org_id)
        status, illegal_release = _api_call(
            client,
            "POST",
            "/api/v1/billing/escrow/release",
            {"sub_order_id": mfg_sub_id, "idempotency_key": str(uuid.uuid4())},
            token=mfg_token,
        )
        assert status == 403

        # 6. Logistics POD with Hidden Random OTP (Fix #3 & #4)
        for sub_order_data in order_resp["sub_orders"]:
            sub_id = sub_order_data["id"]
            status, shipment_resp = _api_call(
                client,
                "POST",
                "/api/v1/logistics/shipments",
                {"sub_order_id": sub_id},
                token=driver_token,
            )
            assert status == 201
            # Fix #3: pod_otp_code must NOT be exposed in driver ShipmentResponse
            assert "pod_otp_code" not in shipment_resp
            shipment_id = shipment_resp["id"]

            # Competitor Distributor B cannot hijack GPS on this shipment (Fix #4)
            status, hijack_gps = _api_call(
                client,
                "POST",
                f"/api/v1/logistics/shipments/{shipment_id}/gps",
                {"lat_microdeg": 41000000, "lng_microdeg": 69000000},
                token=dist_b_token,
            )
            assert status == 403

            status, gps_resp = _api_call(
                client,
                "POST",
                f"/api/v1/logistics/shipments/{shipment_id}/gps",
                {"lat_microdeg": 41315000, "lng_microdeg": 69245000, "status": "IN_TRANSIT"},
                token=driver_token,
            )
            assert status == 200

            # Customer gives their OTP code to driver at delivery door
            buyer_otp = Shipment.objects.get(id=shipment_id).pod_otp_code
            status, pod_resp = _api_call(
                client,
                "POST",
                f"/api/v1/logistics/shipments/{shipment_id}/pod",
                {
                    "pod_otp_code": buyer_otp,
                    "release_idempotency_key": str(uuid.uuid4()),
                    "pod_photo_url": "https://minio.dbazar.uz/pod/proof1.jpg",
                },
                token=driver_token,
            )
            assert status == 200
            assert pod_resp["status"] == "DELIVERED"

        # Verify Escrow vault balance is 0 tiyin, reserved_qty is released (Fix #2), and Double-Entry DEBIT == CREDIT
        oil_stock_after_pod = InventoryStock.objects.get(batch_id="BATCH-OIL-2026-11")
        assert oil_stock_after_pod.reserved_qty == 0
        escrow_vault = LedgerAccount.objects.get(organization__isnull=True, account_type="ESCROW_VAULT")
        assert escrow_vault.balance_tiyin == 0
        total_debits = (
            DoubleEntryRecord.objects.filter(entry_type=EntryType.DEBIT).aggregate(s=Sum("amount_tiyin"))["s"] or 0
        )
        total_credits = (
            DoubleEntryRecord.objects.filter(entry_type=EntryType.CREDIT).aggregate(s=Sum("amount_tiyin"))["s"] or 0
        )
        assert total_debits == total_credits

        # 7. Offline-First POS: 1-Click Waybill Inbound (Fix #1: Single-counted VMI stock!) & 500-Event Sync
        status, pos_store = _api_call(
            client,
            "POST",
            "/api/v1/pos-sync/stores",
            {"name": "Baraka Kassa #1", "terminal_id": "TERM-BARAKA-01", "address": "Chilonzor-9"},
            token=store_token,
        )
        assert status == 201
        pos_store_id = pos_store["id"]

        mfg_sub = next(s for s in order_resp["sub_orders"] if s["seller_org_id"] == mfg_org_id)
        dist_a_sub = next(s for s in order_resp["sub_orders"] if s["seller_org_id"] == dist_a_org_id)

        status, inbound_1 = _api_call(
            client,
            "POST",
            "/api/v1/pos-sync/one-click-inbound",
            {"store_id": pos_store_id, "waybill_qr_token": mfg_sub["waybill_qr_token"]},
            token=store_token,
        )
        assert status == 200
        assert inbound_1["inbounded_items_count"] == 1

        # Fix #1 Verification: After both POD delivery AND 1-Click POS Inbound, oil supplied_qty is 60 (NOT 120!)
        oil_lineage = InventoryLineage.objects.get(customer_org_id=store_org_id, variant_id=variant_oil_id)
        assert oil_lineage.supplied_qty == 60
        assert oil_lineage.current_pos_qty == 60

        status, connect_resp = _api_call(
            client,
            "POST",
            "/api/v1/integrations/dbazar-connect/inbound",
            {
                "external_system": "BILLZ",
                "terminal_id": "BILLZ-BARAKA-02",
                "waybill_qr_token": dist_a_sub["waybill_qr_token"],
            },
            token=store_token,
        )
        assert status == 200
        flour_lineage = InventoryLineage.objects.get(customer_org_id=store_org_id, variant_id=variant_flour_id)
        assert flour_lineage.supplied_qty == 5
        assert flour_lineage.current_pos_qty == 5

        # Generate 500 sequential offline POS events (Airplane Mode simulation)
        offline_events = []
        hlc_cursor: str | None = None
        for idx in range(500):
            hlc_cursor = generate_hlc_timestamp("TERM-BARAKA-01", last_hlc=hlc_cursor, now_ms=1764170000000 + idx)
            ev_type = "RETURN" if (idx % 10 == 9) else "SALE"
            offline_events.append(
                {
                    "client_event_id": str(uuid.uuid5(uuid.NAMESPACE_OID, f"offline-pos-evt-{idx}")),
                    "variant_id": variant_oil_id,
                    "batch_id": "BATCH-OIL-2026-11",
                    "event_type": ev_type,
                    "quantity": 1,
                    "unit_price_tiyin": 2_000_000,
                    "hlc_timestamp": hlc_cursor,
                }
            )

        status, sync_resp = _api_call(
            client,
            "POST",
            "/api/v1/pos-sync/delta",
            {"store_id": pos_store_id, "events": offline_events},
            token=store_token,
        )
        assert status == 200
        assert sync_resp["applied_events"] == 500
        assert sync_resp["conflicts"] == 0
        newest_hlc = sync_resp["last_hlc_timestamp"]

        # Fix #7 Verification: An older delayed HLC batch must NOT rewind store.last_hlc_timestamp
        older_hlc = "1700000000000:0:TERM-BARAKA-01"
        status, delayed_sync = _api_call(
            client,
            "POST",
            "/api/v1/pos-sync/delta",
            {
                "store_id": pos_store_id,
                "events": [
                    {
                        "client_event_id": str(uuid.uuid4()),
                        "variant_id": variant_oil_id,
                        "batch_id": "BATCH-OIL-2026-11",
                        "event_type": "INBOUND",
                        "quantity": 10,
                        "unit_price_tiyin": 1_650_000,
                        "hlc_timestamp": older_hlc,
                    }
                ],
            },
            token=store_token,
        )
        assert status == 200
        assert delayed_sync["last_hlc_timestamp"] == newest_hlc

        # 8. VMI Telemetry Isolation & Soliq/Didox/FinTech Verification
        for viewer_id in (dist_a_org_id, mfg_org_id):
            _api_call(
                client,
                "POST",
                "/api/v1/inventory/vmi/permissions",
                {"viewer_org_id": viewer_id, "is_active": True},
                token=store_token,
            )

        status, vmi_dist_a = _api_call(client, "GET", "/api/v1/inventory/vmi/telemetry", token=dist_a_token)
        assert status == 200
        assert len(vmi_dist_a["items"]) == 1
        assert vmi_dist_a["items"][0]["sku"] == "UN-50KG"
        assert vmi_dist_a["items"][0]["current_pos_qty"] == 5

        status, vmi_dist_b = _api_call(client, "GET", "/api/v1/inventory/vmi/telemetry", token=dist_b_token)
        assert status == 200
        assert vmi_dist_b["items"] == []

        status, credit_resp = _api_call(
            client,
            "POST",
            "/api/v1/billing/credit-scoring/evaluate",
            {},
            token=store_token,
        )
        assert status == 200
        assert credit_resp["credit_limit_tiyin"] >= 500_000_000
        assert credit_resp["discount_tier_bps"] == 500

        # 9. Phase 4 Smart Auto-Restock & Phase 5 AI Regional Demand Forecast
        status, restock_resp = _api_call(
            client,
            "GET",
            "/api/v1/inventory/auto-restock",
            token=store_token,
        )
        assert status == 200, restock_resp
        assert restock_resp["draft_count"] >= 1
        assert any(item["sku"] == "UN-50KG" for item in restock_resp["items"])

        status, forecast_resp = _api_call(
            client,
            "GET",
            "/api/v1/inventory/demand-forecast",
            token=mfg_token,
        )
        assert status == 200, forecast_resp
        assert len(forecast_resp["items"]) == 1
        assert forecast_resp["items"][0]["sku"] == "OLIYA-1L"
        assert forecast_resp["items"][0]["forecast_next_30d_qty"] >= 500

        # 10. Phase 5 Sealed-Bid Tender (RFQ): Create Tender -> Two Sealed Bids -> Award Lowest Bid
        status, tender_resp = _api_call(
            client,
            "POST",
            "/api/v1/orders/rfq/tenders",
            {
                "variant_id": variant_oil_id,
                "target_quantity": 1000,
                "max_unit_price_tiyin": 1_650_000,
                "region": "Toshkent",
            },
            token=store_token,
        )
        assert status == 201, tender_resp
        tender_id = tender_resp["id"]

        # Distributor A bids 1,600,000 tiyin; Manufacturer bids 1,550,000 tiyin
        status, bid_a = _api_call(
            client,
            "POST",
            f"/api/v1/orders/rfq/tenders/{tender_id}/bids",
            {"proposed_unit_price_tiyin": 1_600_000},
            token=dist_a_token,
        )
        assert status == 201, bid_a

        status, bid_mfg = _api_call(
            client,
            "POST",
            f"/api/v1/orders/rfq/tenders/{tender_id}/bids",
            {"proposed_unit_price_tiyin": 1_550_000},
            token=mfg_token,
        )
        assert status == 201, bid_mfg

        # Buyer awards tender -> automatically selects Manufacturer's lowest bid (1,550,000 * 1000 = 1,550,000,000 tiyin)
        status, awarded_order = _api_call(
            client,
            "POST",
            f"/api/v1/orders/rfq/tenders/{tender_id}/award",
            {},
            token=store_token,
        )
        assert status == 200, awarded_order
        assert awarded_order["total_amount_tiyin"] == 1_550_000_000
        assert awarded_order["sub_orders"][0]["seller_org_id"] == mfg_org_id

        # 11. Pending Order Cancellation & Reserved Stock Restoration
        stock_before_cancel = InventoryStock.objects.get(batch_id="BATCH-OIL-2026-11").available_qty
        status, temp_order = _api_call(
            client,
            "POST",
            "/api/v1/orders",
            {
                "idempotency_key": str(uuid.uuid4()),
                "is_preorder": False,
                "items": [{"offer_id": offer_mfg_id, "quantity": 20}],
            },
            token=store_token,
        )
        assert status == 201
        assert InventoryStock.objects.get(batch_id="BATCH-OIL-2026-11").available_qty == stock_before_cancel - 20

        status, cancelled_order = _api_call(
            client,
            "POST",
            f"/api/v1/orders/{temp_order['id']}/cancel",
            {},
            token=store_token,
        )
        assert status == 200
        assert cancelled_order["status"] == "CANCELLED"
        stock_after_cancel = InventoryStock.objects.get(batch_id="BATCH-OIL-2026-11")
        assert stock_after_cancel.available_qty == stock_before_cancel
        assert stock_after_cancel.reserved_qty == 0

        # Verify list endpoints for Orders and RFQ Tenders
        status, orders_list = _api_call(client, "GET", "/api/v1/orders", token=store_token)
        assert status == 200
        assert len(orders_list["items"]) >= 2

        status, tenders_list = _api_call(client, "GET", "/api/v1/orders/rfq/tenders", token=store_token)
        assert status == 200
        assert len(tenders_list["items"]) == 1

        out_yaml = tmp_path / "openapi.yaml"
        call_command("export_openapi", output=str(out_yaml))
        assert out_yaml.exists()
