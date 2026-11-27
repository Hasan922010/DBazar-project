# DBazar — B2B Supply Chain, VMI Telemetry & Offline-First Cloud POS Monorepo

DBazar — ishlab chiqaruvchilar, ulgurji vositachilar (distribyutorlar), logistika va chakana do'konlar (POS kassalar) uchun yagona B2B ta'minot zanjiri platformasi.

## Tezkor Ishga Tushirish (`./run.sh`)

```bash
# 1. Migratsiyalar + OpenAPI -> TS kontrakt + Barcha testlarni o'tkazib, Backend va Frontend serverlarni yoqish:
./run.sh

# 2. Faqat Backend (pytest) va Frontend (node --test) avto-testlarini tekshirish:
./run.sh test

# 3. Serverlarni testlarsiz to'g'ridan-to'g'ri ishga tushirish:
./run.sh serve

# 4. Docker Compose (PostgreSQL 16, Redis 7, Redpanda, ClickHouse, MinIO) ni ko'tarish:
./run.sh docker
```

## Jonli Manillar (`./run.sh` ishga tushganda)

* **Frontend UI Preview (Web-Portal 3 ta kabinet + Drawer, POS Kassa Onlayn/Oflayn, Mobil Xaridor va Haydovchi POD):** http://127.0.0.1:3000
* **Backend OpenAPI 3.1 JSON:** http://127.0.0.1:8001/api/v1/openapi.json
* **Backend Healthcheck:** http://127.0.0.1:8001/healthz/
* **Django Admin Panel:** http://127.0.0.1:8001/admin/ (`Login: admin` / `Parol: dbazar2026`)

## Monorepo Tuzilmasi

* `apps/backend` — Python 3.12+ & Django Modular Monolith (`iam`, `catalog`, `inventory`, `orders`, `billing`, `pos_sync`, `integrations`, `logistics`)
* `apps/web-portal` — Minimalistik B2B Web-Portal (Ishlab chiqaruvchi, Distribyutor va Xaridor kabinetlari + Progressive Disclosure Drawer)
* `apps/pos-client` — Offline-First Cloud POS (`node:sqlite` append-only `pos_stock_events` + HLC + 1-Click QR Avto-Kirim)
* `apps/mobile-app` — Minimalistik Mobil Ilova (4 ta Bottom Tab: Xaridor, Savdo Agenti va Haydovchi GPS/OTP POD rejimi)
* `packages/contracts` — Django'dan eksport qilingan `openapi.yaml` va avto-generatsiya qilingan `src/schema.d.ts`
* `packages/ui-tokens` — Minimalistik dizayn tokenlari (`design-system.css`) va texnik jargonsiz o'zbekcha lug'at (`i18n/uz.json`)
* `packages/shared-utils` — Hybrid Logical Clock (HLC), tiyin formatlash, 17 xonali MXIK validatori va Tiered Pricing hisoblagichi
* `packages/mocks-and-emulators` — Soliq.uz OFD, Tasnif MXIK, Didox EHF, E-Imzo PKCS#7 (`uz-gov-sandbox`) va ESC/POS printer + CAS tarozi (`pos-hardware-sim`)
