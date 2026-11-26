# DBazar — Multi-Agent Orchestration Rules (`AGENTS.md`)

Loyiha 4 ta parallel sub-agent rollariga ajratilgan bo'lib, har bir sub-agent o'z kontekst izolyatsiyasi doirasida ishlaydi:

1. **Backend Architect (`apps/backend/AGENTS.md`)**
   - **Ko'rish doirasi:** `apps/backend`, `packages/contracts`, `packages/mocks-and-emulators/uz-gov-sandbox`
   - **Mas'uliyati:** Django 5 Modular Monolith, Django Ninja REST API, PostgreSQL 16 sxemasi, Double-Entry Ledger (`BigIntegerField` tiyin), Escrow idempotency, VMI `PosTelemetryPermission` izolyatsiyasi, Celery va Channels ASGI, OpenAPI kontrakt eksporti.
   - **Majburiy tekshiruv:** `uv run pytest`, `python manage.py export_openapi`.

2. **Web-Portal Frontend (`apps/web-portal/AGENTS.md`)**
   - **Ko'rish doirasi:** `apps/web-portal`, `packages/contracts`, `packages/ui-tokens`
   - **Mas'uliyati:** Next.js 15 + React + TypeScript, Ishlab chiqaruvchi, Vositachi va Xaridor kabinetlari, `/ui-minimalist-design` qoidalari.
   - **Majburiy tekshiruv:** `pnpm --filter web-portal test`, `playwright-browser-mcp` E2E.

3. **Offline-First POS (`apps/pos-client/AGENTS.md`)**
   - **Ko'rish doirasi:** `apps/pos-client`, `packages/contracts`, `packages/ui-tokens`, `packages/mocks-and-emulators/pos-hardware-sim`
   - **Mas'uliyati:** Electron + React / RN Tablet POS, SQLite append-only `pos_stock_events` + HLC, 1-Click Avto-Kirim, Keyboard-First UX (56px+ tugmalar).
   - **Majburiy tekshiruv:** `pnpm --filter pos-client test`.

4. **Mobile App (`apps/mobile-app/AGENTS.md`)**
   - **Ko'rish doirasi:** `apps/mobile-app`, `packages/contracts`, `packages/ui-tokens`, `packages/shared-utils`
   - **Mas'uliyati:** React Native (Expo Router + NativeWind), Xaridor, Savdo Agenti va Haydovchi (GPS + POD) rejimlari.
   - **Majburiy tekshiruv:** `pnpm --filter mobile-app test`.
