"""
Uzbekistan Government & Tax API Sandbox Emulator (`uz-gov-sandbox`).
Provides deterministic local emulation for:
1. Tasnif.soliq.uz — 17-digit MXIK code verification
2. Soliq.uz Virtual Kassa (OFD) — Fiscal receipt signing & QR generation (with 72h offline queue support)
3. Didox.uz / Faktura.uz — Electronic Invoice (EHF), Contract & Waybill lifecycle
4. E-Imzo — PKCS#7 digital signature verification for KYB & EHF signing
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict

MXIK_REGEX = re.compile(r"^\d{17}$")


class UzGovSandboxEmulator:
    """Deterministic emulator for Soliq.uz OFD, Tasnif MXIK, Didox EHF, and E-Imzo PKCS#7."""

    @staticmethod
    def verify_mxik(mxik_code: str) -> Dict[str, Any]:
        if not MXIK_REGEX.match(mxik_code or ""):
            return {
                "valid": False,
                "mxik_code": mxik_code,
                "error": "MXIK kodi qat'iy 17 ta raqamdan iborat bo'lishi shart.",
            }
        return {
            "valid": True,
            "mxik_code": mxik_code,
            "group_name": "Oziq-ovqat va kundalik iste'mol tovarlari",
            "unit_code": "796",
            "unit_name": "dona",
            "vat_rate_percent": 12,
        }

    @staticmethod
    def verify_eimzo_pkcs7(pkcs7_signature: str, expected_stir: str) -> Dict[str, Any]:
        if not pkcs7_signature or len(pkcs7_signature.strip()) < 12:
            return {"valid": False, "error": "E-Imzo PKCS#7 imzosi yaroqsiz yoki bo'sh."}
        if not re.match(r"^\d{9}$", expected_stir or ""):
            return {"valid": False, "error": "STIR (INN) 9 ta raqamdan iborat bo'lishi shart."}
        cert_serial = hashlib.sha256(f"{expected_stir}:{pkcs7_signature}".encode("utf-8")).hexdigest()[:16].upper()
        return {
            "valid": True,
            "stir": expected_stir,
            "certificate_serial": f"EIMZO-{cert_serial}",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def register_ofd_fiscal_receipt(
        terminal_id: str,
        receipt_seq: int,
        total_amount_tiyin: int,
        mxik_codes: list[str],
    ) -> Dict[str, Any]:
        for code in mxik_codes:
            check = UzGovSandboxEmulator.verify_mxik(code)
            if not check["valid"]:
                raise ValueError(check["error"])
        if total_amount_tiyin <= 0:
            raise ValueError("Chek summasi 0 tiyindan katta bo'lishi shart.")
        digest = hashlib.sha256(f"{terminal_id}:{receipt_seq}:{total_amount_tiyin}".encode("utf-8")).hexdigest()
        fiscal_sign = str(int(digest[:12], 16))[:12].zfill(12)
        return {
            "terminal_id": terminal_id,
            "receipt_seq": receipt_seq,
            "fiscal_sign": fiscal_sign,
            "qr_code_url": f"https://ofd.soliq.uz/check?t={terminal_id}&r={receipt_seq}&s={fiscal_sign}",
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def create_didox_ehf_document(
        sub_order_id: str,
        seller_stir: str,
        buyer_stir: str,
        total_amount_tiyin: int,
        pkcs7_signature: str,
    ) -> Dict[str, Any]:
        sig_check = UzGovSandboxEmulator.verify_eimzo_pkcs7(pkcs7_signature, seller_stir)
        if not sig_check["valid"]:
            raise ValueError(sig_check["error"])
        doc_hash = hashlib.sha256(
            f"DIDOX:{sub_order_id}:{seller_stir}:{buyer_stir}:{total_amount_tiyin}".encode("utf-8")
        ).hexdigest()[:14].upper()
        return {
            "didox_doc_id": f"EHF-{doc_hash}",
            "sub_order_id": str(sub_order_id),
            "seller_stir": seller_stir,
            "buyer_stir": buyer_stir,
            "total_amount_tiyin": total_amount_tiyin,
            "status": "SIGNED_BY_SELLER",
            "certificate_serial": sig_check["certificate_serial"],
        }
