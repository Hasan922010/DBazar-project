"""
Hybrid Logical Clock (HLC) utilities.
"""
from __future__ import annotations

import re
import time
from typing import Tuple

HLC_PATTERN = re.compile(r"^(\d{10,16}):(\d{1,8}):([A-Za-z0-9_-]{1,64})$")


def parse_hlc_timestamp(hlc: str) -> Tuple[int, int, str]:
    match = HLC_PATTERN.match(hlc or "")
    if not match:
        raise ValueError(f"Noto'g'ri HLC vaqt tamg'asi formati: '{hlc}'. Kutilgan format: '<wall_ms>:<counter>:<node_id>'")
    return int(match.group(1)), int(match.group(2)), match.group(3)


def generate_hlc_timestamp(node_id: str, last_hlc: str | None = None, now_ms: int | None = None) -> str:
    physical_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    if not last_hlc:
        return f"{physical_ms}:0:{node_id}"
    last_ms, last_counter, _ = parse_hlc_timestamp(last_hlc)
    if physical_ms > last_ms:
        return f"{physical_ms}:0:{node_id}"
    return f"{last_ms}:{last_counter + 1}:{node_id}"
