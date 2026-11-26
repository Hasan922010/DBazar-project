---
name: db-migration
description: Django ORM PostgreSQL migratsiyalari, organization_id izolyatsiyasi, BigIntegerField (tiyin) va inventory_lineage bog'lanishini tekshirish qoidalari.
---

# DBazar Database Migration & Schema Skill (`/db-migration`)

1. **Valyuta va Narxlar:** Barcha pul maydonlari `models.BigIntegerField` (nomi `*_tiyin` bilan tugashi tavsiya etiladi) bo'lishi shart. `FloatField` yoki `DecimalField` pul summalari uchun ishlatilmasin.
2. **Birlamchi Kalitlar va Indekslar:** Yuqori yuklamali jadvallarda `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` hamda tez-tez qidiriladigan ustunlar (`organization`, `status`, `created_at`, `mxik_code`, `batch_id`) uchun kompozit `models.Index` yaratilsin.
3. **Multi-Tenant va VMI Izolyatsiyasi:** Har bir biznes yozuvi tegishli `Organization` ga bog'lanishi va `InventoryLineage` hamda `PosTelemetryPermission` orqali yetkazib berish zanjiri kuzatilishi shart.
4. **Migratsiya Tekshiruvi:** Har bir model o'zgarishidan so'ng `makemigrations` va `migrate` xatosiz o'tishi hamda `pytest` da migratsiya va constraint testlari tekshirilishi kerak.
