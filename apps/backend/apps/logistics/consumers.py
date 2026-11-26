"""
Django Channels ASGI WebSocket Consumer for Live Driver GPS Telemetry.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

try:
    from channels.generic.websocket import AsyncWebsocketConsumer
except ImportError:  # pragma: no cover
    class AsyncWebsocketConsumer:  # type: ignore[no-redef]
        @classmethod
        def as_asgi(cls) -> Any:
            return None


class LogisticsGpsConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        self.shipment_id = self.scope["url_route"]["kwargs"]["shipment_id"]
        self.group_name = f"shipment_gps_{self.shipment_id}"
        if self.channel_layer is not None:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if not text_data:
            return
        payload = json.loads(text_data)
        lat_microdeg = int(payload.get("lat_microdeg", 0))
        lng_microdeg = int(payload.get("lng_microdeg", 0))
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
