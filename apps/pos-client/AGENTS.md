# Offline-First POS Agent Rules — `apps/pos-client/AGENTS.md`

## Ko'rish doirasi (Scope)
- `apps/pos-client`
- `packages/contracts`
- `packages/ui-tokens`
- `packages/mocks-and-emulators/pos-hardware-sim`

## Majburiy Qoidalar
- Sichqonchasiz (*Keyboard-First*), 56px+ katta kassa tugmalari, `tabular-nums` narxlar.
- Mahalliy SQLite bazasida `UPDATE stock SET qty = X` taqiqlanadi — faqat `pos_stock_events` append-only HLC yozuvlari saqlanadi va `/api/v1/pos-sync/delta` endpointiga yuboriladi.
