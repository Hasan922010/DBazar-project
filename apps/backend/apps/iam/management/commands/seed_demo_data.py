"""
Django management command `seed_demo_data`:
Idempotently seeds realistic B2B organizations, Admin superuser (`admin` / `dbazar2026`),
17-digit MXIK products, Tiered Pricing offers, warehouses, VMI telemetry lineages,
and an active Tender (RFQ) so `./run.sh` works out-of-the-box in both API and Admin panel.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import ProductVariant
from apps.catalog.services import create_product_with_variant, upsert_offer_with_price_tiers
from apps.iam.models import KybStatus, Organization, OrganizationRole, User
from apps.inventory.models import InventoryLineage, Warehouse
from apps.inventory.services import (
    create_warehouse,
    receive_warehouse_stock,
    set_pos_telemetry_permission,
)


class Command(BaseCommand):
    help = "Idempotently seed DBazar demo organizations, Admin superuser, catalog offers, and VMI lineages"

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        admin_org, _ = Organization.objects.get_or_create(
            stir_inn="300000001",
            defaults={
                "name": "DBazar Platform HQ",
                "legal_name": "DBazar Technologies MChJ",
                "role": OrganizationRole.ADMIN,
                "kyb_status": KybStatus.VERIFIED,
                "region": "Toshkent",
            },
        )
        admin_user = User.objects.filter(username="admin").first()
        if admin_user is None:
            admin_user = User.objects.create_superuser(
                username="admin",
                email="admin@dbazar.uz",
                password="dbazar2026",
                phone="+998900000001",
                organization=admin_org,
                role=OrganizationRole.ADMIN,
            )

        mfg_org, _ = Organization.objects.get_or_create(
            stir_inn="301111111",
            defaults={
                "name": "Roison Foods Factory",
                "legal_name": "Roison Foods MChJ",
                "role": OrganizationRole.MANUFACTURER,
                "kyb_status": KybStatus.VERIFIED,
                "eimzo_cert_serial": "EIMZO-ROISON-2026",
                "region": "Toshkent",
            },
        )
        dist_org, _ = Organization.objects.get_or_create(
            stir_inn="302222222",
            defaults={
                "name": "Tashkent Agro Distribyutor",
                "legal_name": "Agro Dist MChJ",
                "role": OrganizationRole.INTERMEDIARY,
                "kyb_status": KybStatus.VERIFIED,
                "eimzo_cert_serial": "EIMZO-AGRO-2026",
                "region": "Toshkent",
            },
        )
        store_org, _ = Organization.objects.get_or_create(
            stir_inn="304444444",
            defaults={
                "name": "Baraka Minimarket #1",
                "legal_name": "Baraka Savdo YaTT",
                "role": OrganizationRole.CUSTOMER,
                "kyb_status": KybStatus.VERIFIED,
                "region": "Toshkent",
                "address": "Toshkent sh., Chilonzor-9, 14-uy",
            },
        )

        # Ensure catalog variants & tiered offers exist
        oil_variant = ProductVariant.objects.filter(sku="OLIYA-1L").first()
        if oil_variant is None:
            _, oil_variant = create_product_with_variant(
                manufacturer=mfg_org,
                name="Kungaboqar yog'i Oliya",
                brand="Oliya",
                description="Yuqori navli tozalangan kungaboqar yog'i",
                sku="OLIYA-1L",
                variant_name="1 Litr PET",
                mxik_code="01901001001000001",
                barcode="4780010010011",
                unit_type="LITER",
                packaging_coefficient=12,
                weight_grams=920,
                category_slug="yog-moy",
            )
        upsert_offer_with_price_tiers(
            seller=mfg_org,
            variant_id=oil_variant.id,
            base_price_tiyin=1_800_000,
            min_order_qty=10,
            tiers=[
                {"min_qty": 10, "max_qty": 49, "unit_price_tiyin": 1_800_000},
                {"min_qty": 50, "max_qty": None, "unit_price_tiyin": 1_650_000},
            ],
        )

        flour_variant = ProductVariant.objects.filter(sku="UN-50KG").first()
        if flour_variant is None:
            _, flour_variant = create_product_with_variant(
                manufacturer=dist_org,
                name="Birinchi navli bug'doy uni",
                brand="Don",
                description="Qozog'iston bug'doyidan tayyorlangan 1-navli un",
                sku="UN-50KG",
                variant_name="50 kg qop",
                mxik_code="01101002001000002",
                barcode="4780020020022",
                unit_type="KG",
                packaging_coefficient=1,
                weight_grams=50000,
                category_slug="un-mahsulotlari",
            )
        upsert_offer_with_price_tiers(
            seller=dist_org,
            variant_id=flour_variant.id,
            base_price_tiyin=22_000_000,
            min_order_qty=2,
            tiers=[
                {"min_qty": 10, "max_qty": None, "unit_price_tiyin": 21_000_000},
            ],
        )

        wh_mfg = Warehouse.objects.filter(code="WH-ROISON-01").first()
        if wh_mfg is None:
            wh_mfg = create_warehouse(
                organization=mfg_org,
                name="Roison Markaziy Ombor",
                code="WH-ROISON-01",
            )
            receive_warehouse_stock(
                organization=mfg_org,
                warehouse_id=wh_mfg.id,
                variant_id=oil_variant.id,
                batch_id="BATCH-OIL-2026-11",
                qty=1200,
                expiry_date=date(2027, 8, 1),
            )

        set_pos_telemetry_permission(customer_org=store_org, viewer_org_id=mfg_org.id, is_active=True)
        set_pos_telemetry_permission(customer_org=store_org, viewer_org_id=dist_org.id, is_active=True)

        InventoryLineage.objects.update_or_create(
            customer_org=store_org,
            variant=oil_variant,
            batch_id="BATCH-OIL-2026-11",
            defaults={
                "manufacturer_org": mfg_org,
                "intermediary_org": mfg_org,
                "supplied_qty": 400,
                "current_pos_qty": 180,
                "sold_pos_qty": 220,
                "min_restock_threshold": 30,
            },
        )
        InventoryLineage.objects.update_or_create(
            customer_org=store_org,
            variant=flour_variant,
            batch_id="BATCH-FLOUR-2026-11",
            defaults={
                "manufacturer_org": dist_org,
                "intermediary_org": dist_org,
                "supplied_qty": 40,
                "current_pos_qty": 4,
                "sold_pos_qty": 36,
                "min_restock_threshold": 5,
            },
        )

        self.stdout.write(
            self.style.SUCCESS("Seeded DBazar demo data (Admin login: admin / dbazar2026)")
        )
