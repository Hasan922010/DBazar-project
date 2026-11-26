---
name: pos-delta-sync
description: expo-sqlite / better-sqlite3 oflayn navbati, HLC vaqt tamg'asi va Django pos_sync da ziddiyatsiz qayta hisoblash qoidalari.
---

# Offline-First POS Delta-Sync & HLC Skill (`/pos-delta-sync`)

1. **Append-Only Event Log:** Kassa qoldig'i hech qachon `UPDATE stock SET qty = X` bilan o'zgartirilmaydi. Har bir harakat (`INBOUND`, `SALE`, `RETURN`, `WRITE_OFF`) alohida `PosStockEvent` sifatida yoziladi.
2. **Hybrid Logical Clock (HLC):** Har bir hodisa `<wall_time_ms>:<logical_counter>:<node_id>` formatidagi HLC tamg'asiga va noyob `client_event_id` (UUID) ga ega bo'ladi.
3. **Idempotent Qabul Qilish:** Django `pos_sync` moduli `client_event_id` bo'yicha dublikatlarni e'tiborsiz qoldiradi (0 ziddiyat), yangi hodisalarni HLC tartibida qo'llab, do'kon qoldig'i va `InventoryLineage` ni atomik yangilaydi.
