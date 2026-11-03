"""Salud del sistema y protocolo."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app import __version__
from app.api.deps import get_container
from app.container import Container
from app.schemas.samples import utcnow
from app.schemas.sessions import ProtocolOut
from app.services.protocol import PROTOCOL

router = APIRouter(prefix="/api", tags=["Sistema"])
Ctx = Annotated[Container, Depends(get_container)]


@router.get("/health", summary="Estado de salud del backend")
def health(ctx: Ctx) -> dict[str, Any]:
    try:
        with ctx.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "version": __version__,
        "database": database,
        "time": utcnow().isoformat(),
        "websocket_clients": ctx.hub.client_count,
        "medical_device": False,
    }


@router.get("/protocol", response_model=ProtocolOut, summary="Fases del protocolo experimental")
def protocol() -> ProtocolOut:
    return PROTOCOL

