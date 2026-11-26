"""
POS Hardware Simulator (`pos-hardware-sim`).
Emulates:
1. Virtual ESC/POS Receipt Printer (converts receipt payload into ESC/POS byte stream & structured preview)
2. Virtual CAS Electronic Scale (returns weight in grams for weight-based SKUs)
3. Virtual 2D Barcode / QR Waybill Scanner
"""
from __future__ import annotations

from typing import Any, Dict, List


class PosHardwareSimulator:
    @staticmethod
    def render_escpos_receipt(
        store_name: str,
        items: List[Dict[str, Any]],
        total_tiyin: int,
        fiscal_qr_url: str,
    ) -> Dict[str, Any]:
        lines = [
            f"=== {store_name} ===",
            "--------------------------------",
        ]
        for item in items:
            som = item["line_total_tiyin"] / 100
            lines.append(f"{item['name']} x{item['qty']}  {som:.2f} UZS")
            lines.append(f"  MXIK: {item['mxik_code']}")
        lines.append("--------------------------------")
        lines.append(f"JAMI: {total_tiyin / 100:.2f} UZS")
        lines.append(f"FISKAL QR: {fiscal_qr_url}")
        text = "\n".join(lines)
        # ESC @ (Initialize) + text + GS V 1 (Cut)
        raw_bytes = b"\x1b@" + text.encode("utf-8") + b"\n\x1dV\x01"
        return {
            "text_preview": text,
            "byte_length": len(raw_bytes),
            "hex_header": raw_bytes[:16].hex(),
            "fiscal_qr_url": fiscal_qr_url,
        }

    @staticmethod
    def read_cas_scale_grams(plu_code: str, simulated_grams: int = 1250) -> Dict[str, Any]:
        if simulated_grams <= 0:
            raise ValueError("Tarozi vazni 0 grammdan katta bo'lishi kerak.")
        return {
            "plu_code": plu_code,
            "weight_grams": simulated_grams,
            "stable": True,
            "protocol": "CAS-TCP-v1",
        }
