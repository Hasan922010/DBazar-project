# DBazar — Google Antigravity CLI (`agy`) Orqali Loyihani Qurish Bo'yicha To'liq Yo'riqnoma

**Loyiha:** DBazar (B2B / B2B2C Ta'minot Zanjiri, VMI Telemetriya va Offline-First Cloud POS)  
**Texnologik Stek:**
* **Frontend (Web):** React + TypeScript + Node.js (Next.js 15 / Tailwind CSS / Shadcn UI)
* **Mobile & POS:** React Native (Expo + TypeScript) va Electron + React (Desktop POS)
* **Backend:** Python 3.12+ + **Django 5** (Django Ninja / DRF, Django Channels ASGI, Celery, Django Unfold Admin)
* **Ma'lumotlar bazasi:** **PostgreSQL 16** (Django ORM, `psycopg` 3) + Redis 7 + Redpanda (Kafka) + ClickHouse + MinIO  

**UX/UI Tamoyili:** Minimalistik, toza va bir ko'rganda hamma (hatto texnikadan yiroq sotuvchi yoki do'kon egasi ham) tushunadigan sodda interfeys  
**Asosiy vosita:** [Google Antigravity CLI (`agy`)](https://antigravity.google/docs/overview/)  
**Mo'ljallangan muddat:** 14–16 hafta (3–4 nafar Senior muhandis + 4 ta parallel AI sub-agent)

> **Django + React/TypeScript Monorepo ustunligi:** Backend (**Python + Django 5**) tayyor Back-Office admin paneli (*Django Unfold*), kuchli ORM tranzaksiyalari (`select_for_update`), Celery fon vazifalari hamda 5-bosqichdagi AI/ML skoring modullarini bitta tilda beradi. Django'dan avtomatik chiqadigan `openapi.yaml` orqali **React + TypeScript** (`web-portal`), **React Native** (`mobile-app`) va **Electron POS** (`pos-client`) uchun TypeScript tiplari (`openapi-typescript`) avtomatik generatsiya qilinadi.

---

## 1. Loyihani Boshlashdan Oldingi Tayyorgarlik (0-Qadam)

### 1.1. O'rnatilishi shart bo'lgan dasturlar

* **Python 3.12+ va `uv`** (yoki `poetry`) — Django 5 Backend (`apps/backend`), Celery, pytest va AI skoring uchun.
* **Node.js 22+ va `pnpm` 9+** — Monorepo boshqaruvi, React + TypeScript Web-Portal (`apps/web-portal`), React Native (`apps/mobile-app`) va Electron POS (`apps/pos-client`) uchun.
* **Docker va Docker Compose** — **PostgreSQL 16**, Redis 7, Redpanda (Kafka), ClickHouse, MinIO va `uz-gov-sandbox` konteynerlari uchun.
* **Expo CLI, Android Studio (SDK/Emulator) va Xcode (macOS da)** — React Native (iOS / Android) mobil va planshet ilovalarini yig'ish hamda testlash uchun.
* **[Google Antigravity CLI (`agy`)](https://github.com/google-antigravity/antigravity-cli)** — terminal agentini ishga tushirish va sub-agentlarni orkestratsiya qilish uchun.

### 1.2. Antigravity CLI va MCP Serverlarini Sozlash

[Antigravity CLI Settings](https://antigravity.google/docs/cli/using/) va [Antigravity CLI Features](https://antigravity.google/docs/cli/features/) asosida `~/.gemini/antigravity-cli/settings.json` faylini quyidagicha sozlang:

```json
{
  "toolPermission": "proceed-in-sandbox",
  "enableTerminalSandbox": true,
  "defaultModel": "gemini-3.8-pro",
  "mcpServers": {
    "postgres-mcp": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://dbazar:dbazar@localhost:5432/dbazar_dev"]
    },
    "playwright-browser-mcp": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "openapi-contracts-mcp": {
      "command": "npx",
      "args": ["-y", "openapi-mcp-server", "./packages/contracts/openapi.yaml"]
    },
    "redpanda-kafka-mcp": {
      "command": "npx",
      "args": ["-y", "kafka-mcp-server", "--brokers", "localhost:9092"]
    }
  }
}
```

### 1.3. Loyiha Papkasini Yaratish va `agy` ni Ishga Tushirish

```bash
mkdir dbazar-monorepo && cd dbazar-monorepo
git init
agy --sandbox
```

---

## 2. Monorepo Tuzilmasi va AI Kontekst Fayllari

[Antigravity CLI Best Practices](https://antigravity.google/docs/cli/best-practices/) ga ko'ra, Python (Django) Backend va Node.js/React/TypeScript Frontend bitta Monorepo ichida quyidagicha tashkil etiladi:

```text
dbazar-monorepo/
├── GEMINI.md                          # Global arxitektura, xavfsizlik va Minimalistik UX/UI qonunlari
├── AGENTS.md                          # 4 ta parallel sub-agent rollari
├── .antigravity/
│   ├── skills/
│   │   ├── db-migration/SKILL.md      # Django makemigrations, BigIntegerField (tiyin) va lineage qoidalari
│   │   ├── soliq-ehf-spec/SKILL.md    # Soliq.uz OFD, MXIK (17 xona), Didox EHF, E-Imzo
│   │   ├── pos-delta-sync/SKILL.md    # React Native/Electron SQLite <-> Django POS Sync & Kafka (HLC)
│   │   ├── b2b-security-audit/SKILL.md# Django RBAC, IDOR, Escrow idempotency va VMI izolyatsiya auditi
│   │   └── ui-minimalist-design/SKILL.md # Minimalistik, sodda va 1 ko'rganda tushunarli UX/UI qoidalari
│   └── hooks/                         # CI/CD va pre-commit tekshiruv skriptlari
├── packages/
│   ├── contracts/                     # Django'dan chiqqan openapi.yaml + avto-generatsiya qilingan TS tiplari
│   ├── ui-tokens/                     # Yagona minimalistik ranglar, shriftlar, ikonlar va sodda o'zbekcha lug'at
│   ├── shared-utils/                  # HLC (Hybrid Logical Clock), tiyin formatlash, MXIK validator (TS)
│   └── mocks-and-emulators/
│       ├── pos-hardware-sim/          # Virtual ESC/POS printer, CAS tarozi, 2D shtrix-kod skaner
│       └── uz-gov-sandbox/            # Soliq.uz OFD, Didox EHF va E-Imzo PKCS#7 Mock Serverlari
├── apps/
│   ├── backend/                       # Python 3.12 + Django 5 Modular Monolith + apps/backend/AGENTS.md
│   │   ├── config/                    # settings, asgi.py (Channels), celery.py, urls.py
│   │   └── apps/
│   │       ├── iam/                   # Auth, JWT, 2FA, OneID/E-Imzo KYB, RBAC
│   │       ├── catalog/               # PIM, MXIK, Tiered Pricing, Elasticsearch sync
│   │       ├── inventory/             # WMS, Redis Lock, Multi-Tier Inventory Lineage
│   │       ├── orders/                # B2B Cart, Pre-order, Order Splitting (SubOrders)
│   │       ├── billing/               # Double-Entry Ledger, Escrow, Split Settlement, Payme/Click/Bank
│   │       ├── pos_sync/              # Append-Only Delta Events, Redpanda/Kafka Producer & Consumer
│   │       ├── integrations/          # Didox EHF, Soliq.uz OFD, DBazar Connect (1C/Billz/Regos API)
│   │       └── logistics/             # Lite-TMS, Django Channels WebSocket GPS, OTP/QR POD
│   ├── web-portal/                    # React + TypeScript + Node.js (Next.js 15) + apps/web-portal/AGENTS.md
│   ├── pos-client/                    # Offline-First POS (Electron + React / RN Tablet) + apps/pos-client/AGENTS.md
│   └── mobile-app/                    # React Native (Expo + TypeScript) — Xaridor, Agent, Haydovchi + apps/mobile-app/AGENTS.md
└── docker-compose.yml                 # PostgreSQL 16, Redis 7, Redpanda, ClickHouse, MinIO
```

### 2.1. Minimalistik va Bir Ko'rganda Tushunarli UX/UI Standarti (`@dbazar/ui-tokens`)

Barcha frontend ilovalar (`web-portal`, `pos-client`, `mobile-app`) quyidagi 6 ta qat'iy dizayn qoidasiga bo'ysunadi:

1. **3-soniya qoidasi (1 ekranda — 1 asosiy maqsad):** Har bir sahifada foydalanuvchi ko'zi darhol eng muhim tugmaga (*Primary CTA*) tushishi kerak (masalan: kassada **"To'lash"**, katalogda **"Savatga"**, haydovchida **"Topshirdim"**).
2. **Sodda va hayotiy til (Zero Jargon):** Foydalanuvchiga ko'rinadigan interfeysda "SKU", "VMI", "Sell-Through", "Escrow", "Sub-order" kabi murakkab atamalar yozilmaydi. O'rniga hamma tushunadigan sodda o'zbekcha yozuvlar ishlatiladi: *"Tovarlar"*, *"Do'kondagi qoldiq"*, *"Xavfsiz to'lov"*, *"1 tugmada kirim"*, *"Nasiya"*.
3. **Toza ranglar palitrasi:** Asosiy fon sof oq (`#FFFFFF`) va yumshoq kulrang (`#F8FAFC`), matn yuqori kontrastli to'q qora (`#0F172A`), aksent sifatida faqat **1 ta asosiy brend rangi** (tugmalar uchun). Holatlar (statuslar) 3 ta tushunarli rangda: yashil (*tayyor / to'landi*), sariq (*yo'lda / kutilmoqda*), qizil (*tugamoqda / qarz*).
4. **Katta tugmalar va ko'p "havo" (Whitespace):** Elementlar bir-biriga yopishib qolmasligi kerak. Mobil va POS tugmalari kamida `48x48px` (kassa asosiy tugmalari `56px+`), narx va summalar `tabular-nums` shriftida katta va aniq yoziladi.
5. **Bosqichma-bosqich ochish (*Progressive Disclosure*):** MXIK kodi, partiya raqami, soliq tafsiloti va murakkab filtrlar asosiy ekranni og'irlashtirmaydi — ular faqat *"Batafsil"* tugmasi bosilganda yon panel (*Drawer*) ichida ochiladi.
6. **Xatosiz va tushunarli ko'rsatmalar:** Bo'sh ekranlarda (*Empty States*) va xatoliklarda texnik kod (`Error 500`) emas, aniq oddiy izoh va bitta harakat tugmasi ko'rsatiladi (masalan: *"Internet uzildi — kassa oflayn ishlashda davom etmoqda"*).

### 2.2. Loyiha Ildizidagi `GEMINI.md` Fayli (Majburiy Qoidalar)

`agy` ni ishga tushirgach, birinchi navbatda loyiha ildizida `GEMINI.md` faylini quyidagi qoidalar bilan yarating:

```markdown
# DBazar — Antigravity CLI Qoidalari

1. ARXITEKTURA: `apps/backend` — Python 3.12 + Django 5 Modular Monolith (Django Ninja + PostgreSQL 16 + Celery + Channels). Django ilovalari (`apps/*`) bir-birining modellarini to'g'ridan-to'g'ri o'zgartirmaydi — faqat Service qatlami yoki Redpanda/Kafka hodisalari orqali bog'lanadi.
2. CONTRACT-FIRST (Django -> TypeScript): Har qanday Django Ninja / Pydantic sxemasi o'zgarganda `python manage.py export_openapi` orqali `packages/contracts/openapi.yaml` yangilanadi va `pnpm --filter @dbazar/contracts generate` bilan React/React Native uchun TypeScript tiplari generatsiya qilinadi.
3. MOLIYA (PostgreSQL): Barcha summalar `BigIntegerField` (tiyinlarda) saqlanadi (`FloatField` taqiqlanadi). Har bir to'lov va Escrow operatsiyasi `transaction.atomic()`, `select_for_update()`, `idempotency_key (UUID v7)` hamda Double-Entry Bookkeeping bilan yoziladi.
4. OFFLINE-FIRST POS: `UPDATE stock SET qty = X` taqiqlanadi. POS (`expo-sqlite` / `better-sqlite3`) faqat o'zgarmas `pos_stock_events` (`INBOUND`, `SALE`, `RETURN`, `WRITE_OFF`) ni HLC tamg'asi bilan saqlaydi va Django `pos_sync` endpointiga Delta-paket yuboradi.
5. VMI IZOLYATSIYASI: Vositachi faqat `pos_telemetry_permissions` ruxsati bor va o'zi yetkazib bergan SKU/partiya (`batch_id`) harakatini ko'ra oladi.
6. MINIMALISTIK UX/UI: Barcha React, Electron POS va React Native ekranlari `@dbazar/ui-tokens` va `/ui-minimalist-design` qoidalariga qat'iy amal qiladi: 1 ekranda 1 asosiy tugma, texnik jargonsiz sodda o'zbekcha matnlar, keng whitespace, 48px+ tugmalar va murakkab detallarni Drawer ichiga yashirish.
7. VERIFICATION LOOP: Backendda `uv run pytest`, Frontend/Mobile/POS da `pnpm test` va `playwright-browser-mcp` 100% yashil bo'lmaguncha vazifani yakunlama.
```

### 2.3. Modul Darajasidagi `AGENTS.md` (Kontekst Izolyatsiyasi)

Token sarfini kamaytirish va sub-agentlarni tezlashtirish uchun 4 ta ilova ichiga lokal `AGENTS.md` fayllari joylashtiriladi:

| Fayl manzili | Ko'rish doirasi (Scope) | Majburiy avto-tekshiruv |
| :--- | :--- | :--- |
| `apps/backend/AGENTS.md` | `apps/backend`, `packages/contracts`, `packages/mocks-and-emulators/uz-gov-sandbox` | `BigIntegerField` (tiyin), `transaction.atomic()` + `select_for_update()`, `uv run pytest`, OpenAPI eksporti |
| `apps/web-portal/AGENTS.md` | `apps/web-portal`, `packages/contracts`, `packages/ui-tokens` | React + TS + Node.js, Minimalistik UI (`/ui-minimalist-design`), sodda o'zbekcha yozuvlar, `playwright-browser-mcp` E2E testi |
| `apps/pos-client/AGENTS.md` | `apps/pos-client`, `packages/contracts`, `packages/ui-tokens`, `packages/mocks-and-emulators/pos-hardware-sim` | Sichqonchasiz (*Keyboard-First*), 56px+ katta kassa tugmalari, *Airplane Mode* SQLite oflayn testi, `pnpm --filter pos-client test` |
| `apps/mobile-app/AGENTS.md` | `apps/mobile-app`, `packages/contracts`, `packages/ui-tokens`, `packages/shared-utils` | React Native (Expo Router + NativeWind), maks 4 ta pastki menyu (Bottom Tab), 48px+ tugmalar, `pnpm --filter mobile-app test` (Jest) |

### 2.4. Maxsus Ko'nikmalar (`.antigravity/skills/`)

[Antigravity Agent Skills](https://antigravity.google/docs/skills/) formatida quyidagi 5 ta `SKILL.md` faylini yarating (terminalda `/` buyrug'i bilan chaqiriladi):

| Slash-buyruq | Papka manzili | Asosiy vazifasi |
| :--- | :--- | :--- |
| `/ui-minimalist-design` | `.antigravity/skills/ui-minimalist-design/SKILL.md` | Minimalistik dizayn tizimi, 3-soniya qoidasi, sodda o'zbekcha terminlar lug'ati, ranglar kontrasti va vizual shovqinsiz ekran standartlari. |
| `/db-migration` | `.antigravity/skills/db-migration/SKILL.md` | Django ORM PostgreSQL migratsiyalari, `organization_id` izolyatsiyasi, `BigIntegerField` va `inventory_lineage` bog'lanishini tekshirish. |
| `/soliq-ehf-spec` | `.antigravity/skills/soliq-ehf-spec/SKILL.md` | Soliq.uz Virtual Kassa API, 17 xonali MXIK validatsiyasi, Didox/Faktura.uz EHF va E-Imzo PKCS#7 standartlari (Python `httpx`/Celery). |
| `/pos-delta-sync` | `.antigravity/skills/pos-delta-sync/SKILL.md` | `expo-sqlite` / `better-sqlite3` oflayn navbati, HLC vaqt tamg'asi va Django `pos_sync` da ziddiyatsiz qayta hisoblash qoidalari. |
| `/b2b-security-audit` | `.antigravity/skills/b2b-security-audit/SKILL.md` | Django RBAC/IDOR sizib chiqishini, narxlar maxfiyligini va Escrow idempotency himoyasini `pytest` bilan avto-testlash. |

---

## 3. Bosqichma-Bosqich Qurish Rejasi va Tayyor `agy` Promptlari

Har bir bosqichni **`/plan` (Rejalash) -> Tasdiqlash -> `/teamwork` (Parallel Bajarish) -> Verification Loop (Testlash)** tartibida olib boring.

### 1-Bosqich: Infratuzilma, Django + PostgreSQL Sxemasi, Kontraktlar va Emulyatorlar (1–2-haftalar)

#### 1.1. Monorepo, Docker Muhiti va Minimalistik UI Tokenlarni Ko'tarish
`agy` terminalida quyidagi promptni bering:

```text
/plan @GEMINI.md qoidalariga asosan Python (Django 5) + Node.js (React/TypeScript/React Native) aralash dbazar-monorepo strukturasini yarat.
1. Root package.json, turbo.json va pnpm-workspace.yaml ni sozla (Expo/React Native Metro bundler va openapi-typescript generatori bilan).
2. apps/backend ichida uv yordamida Python 3.12 + Django 5, Django Ninja (Pydantic v2), django-unfold (Admin), django-channels, celery, psycopg[binary], pytest-django muhitini sozla.
3. docker-compose.yml da PostgreSQL 16, Redis 7, Redpanda (Kafka), ClickHouse va MinIO servislarini yoz.
4. packages/ui-tokens ichida minimalistik dizayn tokenlari va sodda o'zbekcha lug'atni (i18n/uz.json), .antigravity/skills/ ichida 5 ta SKILL.md hamda 4 ta lokal AGENTS.md faylini yarat.
Reja tasdiqlangach, docker compose up -d orqali PostgreSQL 16 va barcha konteynerlar sog'lom ishlashini tekshir.
```

#### 1.2. PostgreSQL Ma'lumotlar Bazasi Sxemasi (Django ORM) va OpenAPI Kontraktlari
```text
/db-migration @apps/backend ichida Django ORM modellari bilan PostgreSQL 16 jadvallarini yarat:
- iam: User, Organization (STIR/INN, KYB status, RBAC rollari: MANUFACTURER, INTERMEDIARY, LOGISTICS, CUSTOMER, ADMIN)
- catalog: Product, ProductVariant (17 xonali MXIK kodi, shtrix-kod, qadoqlash koeffitsienti), Offer, PriceTier (unit_price_tiyin BigIntegerField)
- inventory: Warehouse, InventoryStock (available_qty, reserved_qty, batch_id, expiry_date), InventoryLineage (manufacturer -> intermediary -> customer_pos), PosTelemetryPermission
- orders & logistics: Order, SubOrder, Shipment, TrackingLog
- billing: LedgerAccount, DoubleEntryRecord, EscrowHold (idempotency_key UUIDField unique)
- pos_sync: PosStore, PosShift, PosSale, PosStockEvent (append-only delta + HLC)
makemigrations va migrate ni ishga tushir, postgres-mcp orqali jadvallarni tekshir, Django Ninja dan packages/contracts/openapi.yaml ni eksport qilib, React/RN uchun TypeScript tiplarini generatsiya qil.
```

#### 1.3. POS Hardware va Davlat API Emulyatorlarini Yaratish
```text
@packages/mocks-and-emulators ichida ikkita lokal emulyator paketini qur:
1. pos-hardware-sim: virtual ESC/POS chek printeri (bayt-kodni JSON va matnga o'giruvchi), virtual CAS tarozi (TCP orqali vazn uzatuvchi) va 2D skaner emulyatori.
2. uz-gov-sandbox: Docker konteyner sifatida Soliq.uz OFD (fiskal QR qaytaruvchi), Tasnif.soliq.uz (MXIK tekshiruvchi), Didox EHF (status webhookli) va E-Imzo PKCS#7 mock serveri.
Har ikkala emulyator uchun avto-test yozib, lokal portlarda javob berishini tasdiqla.
```

---

### 2-Bosqich: Core B2B MVP — Django Backend Yadrosi va Minimalistik React Web-Portal (3–6-haftalar)

Bu bosqichda `/teamwork` buyrug'i bilan **Django Backend** va **React Web-Portal** sub-agentlarini parallel ishga tushiring.

#### 2.1. Core Django Backend Modullari (`apps/backend`)
```text
/plan @apps/backend/AGENTS.md asosida Django 5 + Django Ninja + PostgreSQL 16 ichida quyidagi 5 ta app ni ketma-ket qur:
1. iam: JWT (SimpleJWT/Ninja-JWT), 2FA, OneID/E-Imzo KYB verifikatsiya, RBAC ruxsatlari va Django Unfold Admin paneli (Back-Office).
2. catalog: MXIK mahsulot kartochkalari, Tiered Pricing (hajmga qarab narx hisoblash) va PostgreSQL Full-Text / Elasticsearch qidiruvi.
3. inventory: Ombor qoldiqlari, partiya/yaroqlilik muddati va Redis Distributed Lock + PostgreSQL select_for_update() bilan zahiralash.
4. orders: B2B savatcha, Pre-order va Order Splitting (bitta savatchani sotuvchilar bo'yicha SubOrder ga ajratish).
5. billing: Double-Entry Bookkeeping, Escrow (yetkazilguncha muzlatish), Split Settlement hamda Payme/Click/Bank API shlyuzlari (Celery fon vazifalari bilan).
OpenAPI sxemasini va TS tiplarini yangila, har bir app uchun pytest unit va integration testlarini yozib 100% o'tishini tasdiqla.
```

#### 2.2. Minimalistik React + TypeScript Web-Portal (`apps/web-portal` — parallel sub-agentda)
```text
/ui-minimalist-design @apps/web-portal/AGENTS.md, @packages/ui-tokens va @packages/contracts asosida React + TypeScript + Node.js (Next.js 15, Tailwind, Shadcn UI, TanStack Query & Table) da o'ta sodda, toza va bir ko'rganda tushunarli kabinetlarni qur:
- Umumiy qoida: Chap tomonda maksimal 5-6 ta tushunarli menyu bandi, sahifa yuqorisida maksimal 3-4 ta katta raqamli kartochka, jadvallar ortiqcha chiziqlarsiz, MXIK va partiya tafsilotlari yon Drawer da ochiladi.
1. Ishlab chiqaruvchi kabineti: Tovar qo'shish (3 qadamli sodda forma), hajmga qarab narx jadvali, dilerlar ro'yxati.
2. Vositachi (Distribyutor) kabineti: Ombor qoldig'i, kelgan buyurtmalar (1 tugmada tasdiqlash), nasiya limitlari.
3. B2B Xaridor portali: Qidiruv + narxlarni yonma-yon solishtirish, 1 bosishda savatga qo'shish va buyurtma holati chizig'i.
playwright-browser-mcp orqali barcha asosiy oqimlarni E2E testdan o'tkaz va vizual skrinshotlarda elementlar qalashtirilmaganini tekshir.
```

---

### 3-Bosqich: Offline-First Cloud POS, 1-Click Avto-Kirim va Soliq/EHF (7–10-haftalar)

#### 3.1. Minimalistik Offline-First POS Ilovasi (`apps/pos-client`)
```text
/ui-minimalist-design /pos-delta-sync @apps/pos-client/AGENTS.md va @packages/contracts asosida Electron + React + TypeScript (Desktop) va React Native / Expo (Android Planshet) uchun bir ko'rganda istalgan kassir tushunadigan Offline-First POS dasturini qur:
- Kassa ekrani dizayni: Ekran 2 qismga bo'linadi — chapda tezkor qidiruv/skaner va katta tovar plitkalari, o'ngda aniq chek ro'yxati va pastda bitta katta yashil "TO'LASH (F12)" tugmasi (56px+). Oflayn/Onlayn holat tepada bitta kichik nuqta va sodda yozuv bilan ko'rinadi.
1. Mahalliy SQLite bazasi (expo-sqlite / better-sqlite3): tovarlar, MXIK, shtrix-kodlar, kassa smenalari va append-only pos_stock_events (HLC tamg'asi bilan).
2. 1-Click Avto-Kirim: Alohida katta "Tovar qabul qilish (QR)" tugmasi — yuk xati QR-kodini skanerlaganda barcha tovarlar, narxlar va MXIK lar 1 soniyada avtomatik kirim bo'ladi.
3. Tezkor Sotuv va Nasiya Daftari: Skaner, tarozi vazni, naqd/karta/aralash/nasiya to'lovlari (sichqonchasiz klaviatura tugmalari bilan).
4. Hardware Integratsiyasi: @packages/mocks-and-emulators/pos-hardware-sim dagi virtual printer, tarozi va skaner bilan ulash.
5. Delta-Sync Servisi: Internet o'chiq holatda (Airplane Mode) 500 ta ketma-ket sotuv va qaytarish urib, aloqa tiklanganda Django @apps/backend/apps/pos_sync bilan 0 ta ziddiyat bilan sinxronlanishini test orqali tasdiqla.
```

#### 3.2. Soliq.uz, Didox EHF va "DBazar Connect" Tashqi POS API (`apps/backend`)
```text
/soliq-ehf-spec @apps/backend/apps/integrations ichida Python httpx + Celery hamda @packages/mocks-and-emulators/uz-gov-sandbox ga ulangan holda quyidagilarni yarat:
1. Didox / Faktura.uz EHF integratsiyasi: buyurtma tasdiqlanganda elektron shartnoma, EHF va ishonchnomani avtomatik generatsiya qilish va E-Imzo imzosini tekshirish.
2. Soliq.uz Virtual Kassa (OFD): POS cheklari uchun fiskal QR-kod olish va Tasnif.soliq.uz orqali MXIK kodlarini tekshirish (oflayn holatda 72 soatlik navbat mexanizmi bilan).
3. "DBazar Connect" API & Webhook: 1C:Roznitsa, Billz, Regos va F-Apteka ishlatayotgan do'konlar o'z kassasidan chiqmasdan DBazar yuk xatini 1-Click Avto-Kirim qilishi va VMI telemetriya yuborishi uchun ochiq REST API hamda dokumentatsiya.
```

---

### 4-Bosqich: VMI Telemetriya, Auto-Restock va Minimalistik React Native Mobil Ilovasi (11–14-haftalar)

#### 4.1. Multi-Tier Inventory Lineage va ClickHouse Analitikasi
```text
/b2b-security-audit /ui-minimalist-design @apps/backend/apps/inventory va @apps/web-portal da Redpanda (Kafka) hamda ClickHouse ni ula:
1. POS kassasidagi har bir SALE/RETURN/INBOUND hodisasi Django pos_sync -> Redpanda orqali ClickHouse ga yozilib, inventory_lineage zanjirini (Ishlab chiqaruvchi -> Vositachi -> Do'kon) real vaqtda yangilasin.
2. Ishlab chiqaruvchi va Vositachi kabinetida minimalistik tahlil paneli: murakkab grafiklar o'rniga 3 ta aniq ko'rsatkich ("Do'konlardagi qoldiq", "Kunlik sotuv", "Tez tugaydigan tovarlar") va sodda svetofor (yashil/sariq/qizil) indikatorlari.
3. PosTelemetryPermission bo'yicha qat'iy Django RBAC/Tenant izolyatsiya testlarini (pytest) yoz: Vositachi A hech qanday API orqali Vositachi B ning do'kondagi qoldig'ini ko'ra olmasin.
4. Smart Auto-Restock: Do'kon qoldig'i min_stock dan tushganda Celery vazifasi orqali avtomatik buyurtma loyihasini shakllantir (do'kon egasi 1 tugmada tasdiqlaydi).
```

#### 4.2. Minimalistik React Native Mobil Ilova — Xaridor, Agent va Haydovchi (`apps/mobile-app`)
```text
/ui-minimalist-design @apps/mobile-app/AGENTS.md, @packages/ui-tokens va @packages/contracts asosida React Native (Expo Router, NativeWind, TanStack Query, Zustand, expo-location, expo-camera) da maksimal 4 ta pastki menyuli (Bottom Tab), katta tugmali va 1 qo'lda boshqarishga qulay yagona mobil ilovani qur:
1. B2B Xaridor va Savdo Agenti rejimi: Yuqorida katta Qidiruv + Shtrix-kod skaneri, toza tovar kartochkalari (rasm, nomi, ulgurji narx, "+" tugmasi), sodda savatcha va xaritada buyurtma harakati.
2. Haydovchi / Kuryer (Logistics) rejimi: Bitta ekranda faqat joriy manzil, xaritada yo'nalish, mijozga qo'ng'iroq tugmasi va pastda bitta katta holat almashtirish tugmasi ("Ombordan oldim" -> "Yo'lga chiqdim" -> "Topshirdim").
3. Jonli GPS va POD (Proof of Delivery): expo-location (background task) + Django Channels WebSocket orqali GPS koordinatalarni @apps/backend/apps/logistics ga uzatish, yukni QR-kod bilan qabul qilish hamda foto + SMS/OTP kod orqali topshirish.
4. Jest (React Native Testing Library) orqali barcha asosiy ekranlar va oflayn navbat (TanStack Query persistence) testlarini o'tkaz.
```

---

### 5-Bosqich: B2B FinTech (Data-for-Credit), AI Prognoz va High-Load (15–16-haftalar)

#### 5.1. Data-for-Credit Skoring, Python AI Prognoz va Tender (RFQ)
```text
@apps/backend da (Python ekotizimining to'liq kuchi bilan):
1. Data-for-Credit moduli: Do'kon POS telemetriyasini yoqqan bo'lsa, uning oxirgi 3 oylik kassa aylanmasi va intizomi asosida avtomatik B2B nasiya (konsignatsiya) limitini va 3-5% chegirma pog'onasini hisobla.
2. AI Talab Prognozi va Tender (RFQ): Python (scikit-learn / Prophet) asosida hududiy talabni prognozlash hamda yirik xaridorlar uchun yopiq narx taklifli Tender moduli.
3. Kubernetes deployment manifestlari (Uvicorn/Gunicorn ASGI + Celery workers + HPA Auto-scaling), Prometheus/Grafana monitoring va k6 yuklama testi (1,000+ RPS) skriptlarini yarat.
```

#### 5.2. Headless CI/CD Xavfsizlik Auditi (`agy -p`)
Har bir Pull Request da avtomatik tekshiruv ishlashi uchun `.github/workflows/antigravity-audit.yml` ga quyidagi buyruqni qo'shing:

```bash
agy -p "Run /b2b-security-audit on git diff origin/main..HEAD. Verify: 1) zero FloatField currency fields in Django models, 2) all financial writes use transaction.atomic() + idempotency_key + double-entry, 3) no cross-tenant leak in PosTelemetryPermission, 4) UI screens follow /ui-minimalist-design with zero jargon, 5) uv run pytest and all pnpm tests pass." --cwd $(pwd)
```

---

## 4. Bosqichlarni Qabul Qilish Mezonlari (Definition of Done)

| Bosqich | Muddat | Asosiy natija (Deliverable) | Majburiy tekshiruv (Verification Gate) |
| :--- | :--- | :--- | :--- |
| **1-Bosqich** | 1–2-hafta | Django 5 + PostgreSQL 16 sxema, OpenAPI -> TS kontraktlar, `@dbazar/ui-tokens`, Mock emulyatorlar | `docker compose up` yashil, `postgres-mcp` jadvallarni tasdiqlaydi, TS tiplari xatosiz generatsiya bo'ladi. |
| **2-Bosqich** | 3–6-hafta | Core Django Backend + Django Unfold Admin + Minimalistik React/TS Web-Portal | `uv run pytest` va `pnpm test` 100% yashil, Escrow balansida 0 tiyin farq, `playwright-browser-mcp` E2E o'tadi. |
| **3-Bosqich** | 7–10-hafta | Minimalistik Offline POS + 1-Click Kirim + Soliq/Didox + DBazar Connect | Oflayn 500 ta chek -> Django `pos_sync` bilan 0 ziddiyat, virtual chekda fiskal QR-kod mavjud. |
| **4-Bosqich** | 11–14-hafta | VMI Svetofor Analitika + Auto-Restock + Minimalistik React Native Mobil Ilova | `/b2b-security-audit` da 0 ta RBAC/IDOR xato, Kafka -> ClickHouse < 2s, RN Jest testlari yashil. |
| **5-Bosqich** | 15–16-hafta | Data-for-Credit Skoring + Python AI Prognoz + RFQ + Kubernetes + CI/CD Audit | k6 stress-testda 1,000+ RPS (< 200 ms p95), `agy -p` CI auditi xatosiz yakunlanadi. |

---

## 5. Kundalik Ishlash Uchun Tezkor `agy` Buyruqlari

* **`agy --sandbox`** — Terminal agentini xavfsiz izolyatsiya rejimida ishga tushirish.
* **`/plan <vazifa>`** — Kod yozishdan oldin arxitektura rejasini ko'rish va tasdiqlash.
* **`/teamwork`** — Bir nechta sub-agentni (masalan, Django Backend + React Web + React Native Mobile) parallel ishlatish.
* **`/ui-minimalist-design`** — Har qanday Web, POS yoki Mobil ekran yaratishdan oldin minimalistik va sodda UX/UI standartini yoqish.
* **`/fork`** — Asosiy sessiyani buzmasdan eksperimental modul yoki refaktoringni alohida tarmoqda sinash.
* **`/config`** — Model, sandbox va MCP sozlamalarini terminal ichidan tezkor o'zgartirish.
* **`agy -p "<prompt>"`** — Headless rejimda CI/CD, migratsiya yoki xavfsizlik auditini skript orqali ishga tushirish.