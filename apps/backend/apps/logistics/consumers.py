"""
Django Channels ASGI WebSocket Consumer for Live Driver GPS Telemetry.
Verifies JWT token on connect and guards JSON payload parsing.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs

from apps.iam.services import verify_jwt_token

try:
    from channels.generic.websocket import AsyncWebsocketConsumer
except ImportError:  # pragma: no cover
    class AsyncWebsocketConsumer:  # type: ignore[no-redef]
        @classmethod
        def as_asgi(cls) -> Any:
            return None


class LogisticsGpsConsumer(AsyncWebsocketConsumer):
    def _extract_token(self) -> str:
        query_string = (self.scope.get("query_string") or b"").decode("utf-8", errors="ignore")
        params = parse_qs(query_string)
        if "token" in params and params["token"]:
            return params["token"][0]
        for k, v in self.scope.get("headers") or []:
            if k.lower() == b"authorization":
                val = v.decode("utf-8", errors="ignore")
                if val.startswith("Bearer "):
                    return val[7:].strip()
        return ""

    async def connect(self) -> None:
        claims = verify_jwt_token(self._extract_token())
        if not claims:
            await self.close(code=4401)
            return
        self.user_claims = claims
        self.shipment_id = self.scope["url_route"]["kwargs"]["shipment_id"]
        self.group_name = f"shipment_gps_{self.shipment_id}"
        if self.channel_layer is not None:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "group_name") and self.channel_layer is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
            lat_microdeg = int(payload["lat_microdeg"])
            lng_microdeg = int(payload["lng_microdeg"])
        except (ValueError, TypeError, KeyError):
            await self.send(text_data=json.dumps({"error_code": "INVALID_GPS_PAYLOAD"}))
            return

        event = {
            "type": "gps_broadcast",
            "shipment_id": str(self.shipment_id),
            "lat_microdeg": lat_microdeg,
            "lng_microdeg": lng_microdeg,
        }
        if self.channel_layer is not None:
            await self.channel_layer.group_send(self.group_name, event)
        else:
            await self.send(text_data=json.dumps(event))

    async def gps_broadcast(self, event: dict[str, Any]) -> None:
        await self.send(text_data=json.dumps(event))
