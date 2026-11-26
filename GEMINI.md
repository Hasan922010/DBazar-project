# DBazar — Antigravity CLI Qoidalari

1. ARXITEKTURA: `apps/backend` — Python 3.12+ + Django 5 Modular Monolith (Django Ninja + PostgreSQL 16 + Celery + Channels). Django ilovalari (`apps/*`) bir-birining modellarini to'g'ridan-to'g'ri o'zgartirmaydi — faqat Service qatlami yoki Redpanda/Kafka hodisalari orqali bog'lanadi.
2. CONTRACT-FIRST (Django -> TypeScript): Har qanday Django Ninja / Pydantic sxemasi o'zgarganda `python manage.py export_openapi` orqali `packages/contracts/openapi.yaml` yangilanadi va `pnpm --filter @dbazar/contracts generate` bilan React/React Native uchun TypeScript tiplari generatsiya qilinadi.
3. MOLIYA (PostgreSQL): Barcha summalar `BigIntegerField` (tiyinlarda) saqlanadi (`FloatField` taqiqlanadi). Har bir to'lov va Escrow operatsiyasi `transaction.atomic()`, `select_for_update()`, `idempotency_key (UUID)` hamda Double-Entry Bookkeeping bilan yoziladi.
4. OFFLINE-FIRST POS: `UPDATE stock SET qty = X` taqiqlanadi. POS (`expo-sqlite` / `better-sqlite3`) faqat o'zgarmas `pos_stock_events` (`INBOUND`, `SALE`, `RETURN`, `WRITE_OFF`) ni HLC tamg'asi bilan saqlaydi va Django `pos_sync` endpointiga Delta-paket yuboradi.
5. VMI IZOLYATSIYASI: Vositachi faqat `pos_telemetry_permissions` ruxsati bor va o'zi yetkazib bergan SKU/partiya (`batch_id`) harakatini ko'ra oladi.
6. MINIMALISTIK UX/UI: Barcha React, Electron POS va React Native ekranlari `@dbazar/ui-tokens` va `/ui-minimalist-design` qoidalariga qat'iy amal qiladi: 1 ekranda 1 asosiy tugma, texnik jargonsiz sodda o'zbekcha matnlar, keng whitespace, 48px+ tugmalar va murakkab detallarni Drawer ichiga yashirish.
7. VERIFICATION LOOP: Backendda `uv run pytest`, Frontend/Mobile/POS da `pnpm test` va `playwright-browser-mcp` 100% yashil bo'lmaguncha vazifani yakunlama.
