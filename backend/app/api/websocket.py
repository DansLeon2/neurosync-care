"""WebSocket de tiempo real: ``/ws/stream``.

Mensajes servidor → cliente (JSON):
* ``hello``  : estado inicial (fuente, último fotograma, sesión activa).
* ``frame``  : valores más recientes (potencias por sensor/banda, calidad, batería…).
* ``status`` : cambios del estado de la fuente (conexión, desconexión, errores).
* ``session``: eventos de sesión/fase (iniciada, fase iniciada/terminada, finalizada).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["Tiempo real"])
log = logging.getLogger(__name__)


@router.websocket("/ws/stream")
async def stream(ws: WebSocket) -> None:
    ctx = ws.app.state.container
    await ws.accept()
    queue = ctx.hub.subscribe()
    try:
        active = ctx.sessions.active()
        await ws.send_json(
            {
                "type": "hello",
                "status": ctx.acquisition.status().model_dump(mode="json"),
                "frame": ctx.pipeline.state.frame(),
                "session": active.model_dump(mode="json") if active else None,
            }
        )

        async def pump() -> None:
            while True:
                await ws.send_json(await queue.get())

        async def drain() -> None:  # detecta cierre del cliente (ignora lo que envíe)
            while True:
                await ws.receive_text()

        tasks = [asyncio.create_task(pump()), asyncio.create_task(drain())]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        for t in done:
            exc = t.exception()
            if exc and not isinstance(exc, WebSocketDisconnect | RuntimeError):
                log.warning("WebSocket terminó con error: %r", exc)
    except WebSocketDisconnect:
        pass
    finally:
        ctx.hub.unsubscribe(queue)
        with contextlib.suppress(Exception):
            await ws.close()

