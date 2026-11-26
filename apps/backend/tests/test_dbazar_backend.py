"""
Comprehensive Verification & B2B Security Audit Test Suite for DBazar Backend.
Covers all requirements from `reja.md`, `GEMINI.md`, and `/b2b-security-audit`:
1. Zero FloatField currency/model audit (all monetary fields strictly BigIntegerField in tiyin)
2. IAM registration, JWT authentication, RBAC guards & E-Imzo PKCS#7 KYB verification
3. Catalog 17-digit MXIK validation & Tiered Pricing calculation in tiyin
4. Multi-vendor B2B Cart Checkout, automatic Order Splitting into SubOrders & FEFO stock reservation
5. Double-Entry Bookkeeping (DEBIT == CREDIT invariant), Escrow idempotency & Split Settlement (0 tiyin drift)
6. Offline-First POS 1-Click Waybill Auto-Inbound & 500-event Airplane Mode HLC Delta-Sync (0 conflicts)
7. Strict VMI Telemetry Isolation (`PosTelemetryPermission` + `InventoryLineage` cross-tenant leak prevention)
8. Soliq.uz OFD fiscal QR, Didox EHF, DBazar Connect external POS API & Data-for-Credit B2B scoring
9. Contract-First OpenAPI 3.1.0 schema export verification (`packages/contracts/openapi.yaml`)
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
from apps.orders.models import Order, SubOrder
from apps.pos_sync.models import PosStockEvent
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
        """
        GEMINI.md Rule #3 & /b2b-security-audit:
        Verify zero FloatField exists in any domain app model, and every *_tiyin field is BigIntegerField.
        """
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

        # ---------------------------------------------------------------------
        # 1. IAM Registration & E-Imzo PKCS#7 KYB Verification
        # ---------------------------------------------------------------------
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
        assert kyb_resp["eimzo_cert_serial"].startswith("EIMZO-")

        # ---------------------------------------------------------------------
        # 2. Catalog 17-Digit MXIK Validation & Tiered Pricing
        # ---------------------------------------------------------------------
        # Reject invalid 10-digit MXIK code
        status, bad_mxik = _api_call(
            client,
            "POST",
            "/api/v1/catalog/products",
            {
                "name": "Noto'g'ri MXIK Tovar",
                "sku": "BAD-SKU",
                "variant_name": "1L",
                "mxik_code": "1234567890",
                "barcode": "4780000001",
            },
            token=mfg_token,
        )
        assert status == 422

        # Create valid product variants with 17-digit MXIK
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
        assert status == 201, variant_oil
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
        assert status == 201, variant_flour
        variant_flour_id = variant_flour["id"]

        # Create Tiered Pricing Offer from Manufacturer (Oliya 1L: base 18,000 UZS = 1,800,000 tiyin; >=50 pcs: 16,500 UZS = 1,650,000 tiyin)
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
        assert status == 201, offer_mfg
        offer_mfg_id = offer_mfg["id"]

        # Create Offer from Distributor A (Flour 50kg: 220,000 UZS = 22,000,000 tiyin)
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

        # Verify Tiered Pricing calculator endpoint
        status, calc_resp = _api_call(
            client,
            "POST",
            f"/api/v1/catalog/offers/{offer_mfg_id}/calculate-price",
            {"quantity": 60},
        )
        assert status == 200
        assert calc_resp["unit_price_tiyin"] == 1_650_000
        assert calc_resp["total_price_tiyin"] == 99_000_000

        # ---------------------------------------------------------------------
        # 3. Warehouse Creation & Batch Stock Receipt
        # ---------------------------------------------------------------------
        status, wh_mfg = _api_call(
            client,
            "POST",
            "/api/v1/inventory/warehouses",
            {"name": "Roison Markaziy Ombor", "code": "WH-MFG-01"},
            token=mfg_token,
        )
        assert status == 201
        status, _ = _api_call(
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
        assert status == 201

        status, wh_dist_a = _api_call(
            client,
            "POST",
            "/api/v1/inventory/warehouses",
            {"name": "Distribyutor A Ombori", "code": "WH-DISTA-01"},
            token=dist_a_token,
        )
        assert status == 201
        status, _ = _api_call(
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
        assert status == 201

        # ---------------------------------------------------------------------
        # 4. Multi-Vendor B2B Cart Checkout & Order Splitting (SubOrders)
        # ---------------------------------------------------------------------
        order_idemp_key = str(uuid.uuid4())
        order_payload = {
            "idempotency_key": order_idemp_key,
            "is_preorder": False,
            "delivery_address": "Toshkent sh., Chilonzor-9, Baraka Minimarket",
            "items": [
                {"offer_id": offer_mfg_id, "quantity": 60},     # 60 * 1,650,000 = 99,000,000 tiyin
                {"offer_id": offer_dist_a_id, "quantity": 5},   # 5 * 22,000,000 = 110,000,000 tiyin
            ],
        }
        status, order_resp = _api_call(client, "POST", "/api/v1/orders", order_payload, token=store_token)
        assert status == 201, order_resp
        assert order_resp["total_amount_tiyin"] == 209_000_000
        assert len(order_resp["sub_orders"]) == 2

        # Re-sending with same idempotency_key returns exact same order without double stock reservation
        status, order_dup = _api_call(client, "POST", "/api/v1/orders", order_payload, token=store_token)
        assert status == 201
        assert order_dup["id"] == order_resp["id"]
        assert Order.objects.count() == 1
        assert SubOrder.objects.count() == 2

        oil_stock = InventoryStock.objects.get(batch_id="BATCH-OIL-2026-11")
        assert oil_stock.available_qty == 440
        assert oil_stock.reserved_qty == 60

        # ---------------------------------------------------------------------
        # 5. Double-Entry Ledger Top-Up, Escrow Hold Idempotency & Split Settlement
        # ---------------------------------------------------------------------
        topup_idemp = str(uuid.uuid4())
        status, wallet_resp = _api_call(
            client,
            "POST",
            "/api/v1/billing/wallet/topup",
            {
                "amount_tiyin": 300_000_000,
                "idempotency_key": topup_idemp,
                "provider": "PAYME",
            },
            token=store_token,
        )
        assert status == 200
        assert wallet_resp["balance_tiyin"] == 300_000_000

        # Hold payment in Escrow (and test idempotency on retry)
        escrow_hold_idemp = str(uuid.uuid4())
        hold_payload = {
            "order_id": order_resp["id"],
            "idempotency_key": escrow_hold_idemp,
            "payment_provider": "PAYME",
        }
        status, escrow_list_1 = _api_call(client, "POST", "/api/v1/billing/escrow/hold", hold_payload, token=store_token)
        assert status == 200, escrow_list_1
        status, escrow_list_2 = _api_call(client, "POST", "/api/v1/billing/escrow/hold", hold_payload, token=store_token)
        assert status == 200
        assert len(escrow_list_1["items"]) == 2
        assert EscrowHold.objects.count() == 2

        # Verify buyer wallet deducted only once: 300,000,000 - 209,000,000 = 91,000,000 tiyin
        buyer_wallet = LedgerAccount.objects.get(organization_id=store_org_id, account_type="BUYER_WALLET")
        assert buyer_wallet.balance_tiyin == 91_000_000

        # Deliver both SubOrders via Logistics OTP Proof of Delivery -> triggers Escrow Split Settlement
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
            shipment_id = shipment_resp["id"]
            otp_code = shipment_resp["pod_otp_code"]

            # Update GPS & status ("Yo'lga chiqdim")
            status, gps_resp = _api_call(
                client,
                "POST",
                f"/api/v1/logistics/shipments/{shipment_id}/gps",
                {
                    "lat_microdeg": 41315000,
                    "lng_microdeg": 69245000,
                    "status": "IN_TRANSIT",
                },
                token=driver_token,
            )
            assert status == 200
            assert gps_resp["status"] == "IN_TRANSIT"

            # Confirm POD with OTP -> releases Escrow with Split Settlement
            status, pod_resp = _api_call(
                client,
                "POST",
                f"/api/v1/logistics/shipments/{shipment_id}/pod",
                {
                    "pod_otp_code": otp_code,
                    "release_idempotency_key": str(uuid.uuid4()),
                    "pod_photo_url": "https://minio.dbazar.uz/pod/proof1.jpg",
                },
                token=driver_token,
            )
            assert status == 200
            assert pod_resp["status"] == "DELIVERED"

        # Verify Escrow vault balance is 0 tiyin and Seller + Platform balances match 100% (0 tiyin drift)
        escrow_vault = LedgerAccount.objects.get(organization__isnull=True, account_type="ESCROW_VAULT")
        assert escrow_vault.balance_tiyin == 0

        total_debits = (
            DoubleEntryRecord.objects.filter(entry_type=EntryType.DEBIT).aggregate(s=Sum("amount_tiyin"))["s"] or 0
        )
        total_credits = (
            DoubleEntryRecord.objects.filter(entry_type=EntryType.CREDIT).aggregate(s=Sum("amount_tiyin"))["s"] or 0
        )
        assert total_debits == total_credits
        assert sum(acc.balance_tiyin for acc in LedgerAccount.objects.all()) == 0

        # ---------------------------------------------------------------------
        # 6. Offline-First POS: 1-Click Waybill Inbound & 500-Event Airplane Mode Sync
        # ---------------------------------------------------------------------
        status, pos_store = _api_call(
            client,
            "POST",
            "/api/v1/pos-sync/stores",
            {
                "name": "Baraka Kassa #1",
                "terminal_id": "TERM-BARAKA-01",
                "address": "Chilonzor-9",
            },
            token=store_token,
        )
        assert status == 201
        pos_store_id = pos_store["id"]

        # Test 1-Click Waybill Inbound on the first SubOrder waybill QR token (idempotent when scanned twice)
        waybill_qr_1 = order_resp["sub_orders"][0]["waybill_qr_token"]
        status, inbound_1 = _api_call(
            client,
            "POST",
            "/api/v1/pos-sync/one-click-inbound",
            {"store_id": pos_store_id, "waybill_qr_token": waybill_qr_1},
            token=store_token,
        )
        assert status == 200
        assert inbound_1["inbounded_items_count"] == 1
        status, inbound_1_retry = _api_call(
            client,
            "POST",
            "/api/v1/pos-sync/one-click-inbound",
            {"store_id": pos_store_id, "waybill_qr_token": waybill_qr_1},
            token=store_token,
        )
        assert status == 200
        assert inbound_1_retry["inbounded_items_count"] == 0

        # Test DBazar Connect external POS (Billz / 1C) 1-Click Inbound on the second SubOrder waybill
        waybill_qr_2 = order_resp["sub_orders"][1]["waybill_qr_token"]
        status, connect_resp = _api_call(
            client,
            "POST",
            "/api/v1/integrations/dbazar-connect/inbound",
            {
                "external_system": "BILLZ",
                "terminal_id": "BILLZ-BARAKA-02",
                "waybill_qr_token": waybill_qr_2,
            },
            token=store_token,
        )
        assert status == 200
        assert connect_resp["is_pos_inbounded"] is True

        # Generate 500 sequential offline POS events (Airplane Mode simulation: 450 SALE + 50 RETURN)
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
        assert status == 200, sync_resp
        assert sync_resp["applied_events"] == 500
        assert sync_resp["skipped_duplicates"] == 0
        assert sync_resp["conflicts"] == 0

        # Replay the exact same 500 events (simulating network retry) -> 0 applied, 500 skipped, 0 conflicts!
        status, sync_retry = _api_call(
            client,
            "POST",
            "/api/v1/pos-sync/delta",
            {"store_id": pos_store_id, "events": offline_events},
            token=store_token,
        )
        assert status == 200
        assert sync_retry["applied_events"] == 0
        assert sync_retry["skipped_duplicates"] == 500
        assert sync_retry["conflicts"] == 0

        # ---------------------------------------------------------------------
        # 7. VMI Telemetry Tenant & Batch Isolation Audit (/b2b-security-audit)
        # ---------------------------------------------------------------------
        # Before permission is granted, Manufacturer and Distributor A see 0 items
        status, vmi_before = _api_call(client, "GET", "/api/v1/inventory/vmi/telemetry", token=dist_a_token)
        assert status == 200
        assert vmi_before["items"] == []

        # Customer Store grants VMI permission to Distributor A and Manufacturer (NOT Distributor B)
        for viewer_id in (dist_a_org_id, mfg_org_id):
            status, perm_resp = _api_call(
                client,
                "POST",
                "/api/v1/inventory/vmi/permissions",
                {"viewer_org_id": viewer_id, "is_active": True},
                token=store_token,
            )
            assert status == 200
            assert perm_resp["is_active"] is True

        # Distributor A ONLY sees the flour batch it supplied (NOT Manufacturer's oil batch!)
        status, vmi_dist_a = _api_call(client, "GET", "/api/v1/inventory/vmi/telemetry", token=dist_a_token)
        assert status == 200
        assert len(vmi_dist_a["items"]) == 1
        assert vmi_dist_a["items"][0]["sku"] == "UN-50KG"

        # Distributor B (competitor with no permission and no lineage) sees 0 items!
        status, vmi_dist_b = _api_call(client, "GET", "/api/v1/inventory/vmi/telemetry", token=dist_b_token)
        assert status == 200
        assert vmi_dist_b["items"] == []

        # Even if Customer mistakenly grants permission to Distributor B, Distributor B still sees 0 items
        # because Distributor B is NOT in the InventoryLineage of any batch at Customer Store!
        dist_b_org_id = dist_b_auth["user"]["organization"]["id"]
        _api_call(
            client,
            "POST",
            "/api/v1/inventory/vmi/permissions",
            {"viewer_org_id": dist_b_org_id, "is_active": True},
            token=store_token,
        )
        status, vmi_dist_b_after = _api_call(client, "GET", "/api/v1/inventory/vmi/telemetry", token=dist_b_token)
        assert status == 200
        assert vmi_dist_b_after["items"] == []

        # ---------------------------------------------------------------------
        # 8. Soliq.uz OFD Fiscal Receipt, Didox EHF & Data-for-Credit Scoring
        # ---------------------------------------------------------------------
        dist_a_suborder = next(s for s in order_resp["sub_orders"] if s["seller_org_id"] == dist_a_org_id)
        status, ehf_resp = _api_call(
            client,
            "POST",
            "/api/v1/integrations/didox/ehf",
            {
                "sub_order_id": dist_a_suborder["id"],
                "pkcs7_signature": "MIAGCSqGSIb3DQEHAqCAMIACAQExDzANBglghkgBZQMEAgEFADCABgkqhkiG9w0BBwEAAKCAMII=",
            },
            token=dist_a_token,
        )
        assert status == 201, ehf_resp
        assert ehf_resp["didox_doc_id"].startswith("EHF-")
        assert ehf_resp["status"] == "SIGNED_BY_SELLER"

        status, ofd_resp = _api_call(
            client,
            "POST",
            "/api/v1/integrations/soliq/ofd-receipt",
            {
                "store_id": pos_store_id,
                "client_sale_id": str(uuid.uuid4()),
                "receipt_seq": 1001,
                "payment_method": "CARD",
                "total_amount_tiyin": 4_000_000,
                "mxik_codes": [mxik_oil],
                "hlc_timestamp": generate_hlc_timestamp("TERM-BARAKA-01"),
            },
            token=store_token,
        )
        assert status == 201, ofd_resp
        assert "ofd.soliq.uz/check" in ofd_resp["qr_code_url"]

        # Evaluate Phase 5 Data-for-Credit B2B Credit Limit & 5% (500 bps) VMI Discount Tier
        status, credit_resp = _api_call(
            client,
            "POST",
            "/api/v1/billing/credit-scoring/evaluate",
            {},
            token=store_token,
        )
        assert status == 200, credit_resp
        assert credit_resp["credit_limit_tiyin"] >= 500_000_000
        assert credit_resp["discount_tier_bps"] == 500

        # ---------------------------------------------------------------------
        # 9. Contract-First OpenAPI 3.1.0 Export Verification
        # ---------------------------------------------------------------------
        out_yaml = tmp_path / "openapi.yaml"
        call_command("export_openapi", output=str(out_yaml))
        assert out_yaml.exists()
        content = out_yaml.read_text(encoding="utf-8")
        assert "openapi: 3.1.0" in content
        assert "/api/v1/orders" in content
        assert "/api/v1/pos-sync/delta" in content
        assert "/api/v1/inventory/vmi/telemetry" in content
