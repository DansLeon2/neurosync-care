"""Difusión de mensajes en tiempo real a los clientes WebSocket."""

from __future__ import annotations

import asyncio
from typing import Any


class StreamHub:
    """Cada cliente tiene una cola acotada: un cliente lento pierde mensajes antiguos, no bloquea al resto."""

    def __init__(self, queue_size: int = 100) -> None:
        self._clients: set[asyncio.Queue[dict[str, Any]]] = set()
        self._queue_size = queue_size

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_size)
        self._clients.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._clients.discard(queue)

    def broadcast(self, message: dict[str, Any]) -> None:
        for queue in list(self._clients):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(message)

