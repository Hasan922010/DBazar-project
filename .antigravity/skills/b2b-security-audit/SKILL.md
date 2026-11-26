---
name: b2b-security-audit
description: Django RBAC/IDOR sizib chiqishini, narxlar maxfiyligini, VMI izolyatsiyasini va Escrow idempotency himoyasini pytest bilan avto-testlash.
---

# B2B Security & Financial Integrity Audit (`/b2b-security-audit`)

1. **Zero FloatField:** Hech bir Django modelida pul qiymati uchun `FloatField` bo'lmasligi shart.
2. **Double-Entry & Escrow Idempotency:** Har bir moliyaviy operatsiya `idempotency_key`, `transaction.atomic()`, `select_for_update()` va juft yozuv (`DEBIT` == `CREDIT`) bilan himoyalangan bo'lishi kerak.
3. **VMI Tenant Izolyatsiyasi:** Vositachi A hech qachon Vositachi B yetkazib bergan partiya (`batch_id`) yoki ruxsat bermagan do'kon (`PosTelemetryPermission.is_active=True` bo'lmagan) qoldig'ini ko'ra olmasligi shart.
4. **RBAC & IDOR:** Tashkilot foydalanuvchisi faqat o'z `organization_id` siga tegishli buyurtma, ombor va hisoblarni boshqara oladi.
