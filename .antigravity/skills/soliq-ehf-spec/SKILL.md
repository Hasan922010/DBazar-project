---
name: soliq-ehf-spec
description: Soliq.uz Virtual Kassa API, 17 xonali MXIK validatsiyasi, Didox/Faktura.uz EHF va E-Imzo PKCS#7 standartlari.
---

# Soliq.uz OFD, MXIK va Didox EHF Spetsifikatsiyasi (`/soliq-ehf-spec`)

1. **17 Xonali MXIK Validatsiyasi:** Har bir `ProductVariant.mxik_code` faqat 17 ta raqamdan (`^\d{17}$`) iborat bo'lishi shart.
2. **Soliq.uz Virtual Kassa (OFD):** POS sotuv cheklari uchun fiskal belgi (`terminal_id`, `receipt_seq`, `fiscal_sign`, `qr_code_url`) shakllantiriladi. Internet uzilganda 72 soatgacha oflayn navbatda saqlanadi.
3. **Didox / Faktura.uz EHF:** B2B `SubOrder` tasdiqlanganda elektron hisobvaraq-faktura (EHF) hujjati va E-Imzo PKCS#7 imzosi tekshiriladi.
4. **DBazar Connect:** Tashqi POS tizimlari (1C, Billz, Regos) uchun 1-Click Avto-Kirim yuk xati va VMI telemetriya webhook/API formatini taqdim etadi.
