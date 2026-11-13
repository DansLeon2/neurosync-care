"""Difusión de mensajes en tiempo real a los clientes WebSocket."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from threading import RLock
from typing import Any


class StreamHub:
    """Cada cliente tiene una cola acotada: un cliente lento pierde mensajes antiguos, no bloquea al resto."""

    def __init__(self, queue_size: int = 100) -> None:
        self._clients: dict[asyncio.Queue[dict[str, Any]], asyncio.AbstractEventLoop] = {}
        self._queue_size = queue_size
        self._lock = RLock()

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_size)
        with self._lock:
            self._clients[queue] = asyncio.get_running_loop()
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._clients.pop(queue, None)

    def broadcast(self, message: dict[str, Any]) -> None:
        # Los endpoints síncronos se ejecutan en hilos de FastAPI.
        # Un fotograma debe conservar sus valores en el instante de publicación.
        snapshot = deepcopy(message)
        with self._lock:
            clients = list(self._clients.items())
        try:
            current = asyncio.get_running_loop()
        except RuntimeError:
            current = None
        for queue, loop in clients:
            if loop.is_closed():
                self.unsubscribe(queue)
                continue
            if current is loop:
                self._deliver(queue, snapshot)
            else:
                try:
                    loop.call_soon_threadsafe(self._deliver, queue, snapshot)
                except RuntimeError:
                    self.unsubscribe(queue)

    def _deliver(self, queue: asyncio.Queue, message: dict[str, Any]) -> None:
        with self._lock:
            if queue not in self._clients:
                return
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(message)

