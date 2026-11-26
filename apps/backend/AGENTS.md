# Backend Architect — `apps/backend/AGENTS.md`

## Ko'rish doirasi (Scope)
- `apps/backend`
- `packages/contracts`
- `packages/mocks-and-emulators/uz-gov-sandbox`

## Arxitektura Qoidalari (Modular Monolith)
1. **Service-Layer Isolation:** `apps/backend/apps/*` modullari (`iam`, `catalog`, `inventory`, `orders`, `billing`, `pos_sync`, `integrations`, `logistics`) boshqa modul modellariga to'g'ridan-to'g'ri `.save()`, `.update()` yoki `.delete()` chaqirmaydi. Barcha yozish operatsiyalari o'sha modulning `services.py` qatlami orqali bajariladi.
2. **Moliyaviy Aniqlik (`BigIntegerField` — Tiyin):**
   - Hech bir modelda pul/narx uchun `FloatField` ishlatilmaydi.
   - Barcha summalar `BigIntegerField` (1 so'm = 100 tiyin) ko'rinishida saqlanadi.
   - Balans, zahiralash va Escrow operatsiyalari `transaction.atomic()` va `select_for_update()` bilan himoyalanadi.
   - Har bir to'lov va Escrow operatsiyasi `idempotency_key` (unique UUID) va Double-Entry (`DEBIT` / `CREDIT` yig'indisi = 0) qoidasiga bo'ysunadi.
3. **Offline-First POS (`pos_sync`):**
   - Kassa qoldig'i to'g'ridan-to'g'ri ustidan yozilmaydi. Faqat `PosStockEvent` (`INBOUND`, `SALE`, `RETURN`, `WRITE_OFF`) append-only tarzda HLC (`hlc_timestamp`) va `event_id` (idempotent) bilan qabul qilinadi.
4. **VMI Telemetriya Izolyatsiyasi (`PosTelemetryPermission`):**
   - Vositachi (yoki Ishlab chiqaruvchi) faqat do'kon (`customer_org`) tomonidan faol ruxsat berilgan va `InventoryLineage` zanjirida o'zi yetkazib bergan `batch_id` / `variant_id` qoldiqlarinigina ko'ra oladi.
5. **Contract-First OpenAPI:**
   - Har qanday endpoint yoki Pydantic sxema o'zgarganda `python manage.py export_openapi` buyrug'i orqali `packages/contracts/openapi.yaml` yangilanadi.

## Majburiy Avto-Tekshiruv
- `uv run pytest` (100% testlar yashil bo'lishi shart)
- `uv run python manage.py check`
- `uv run python manage.py export_openapi`
