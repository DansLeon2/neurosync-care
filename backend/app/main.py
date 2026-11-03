"""Aplicación FastAPI de NeuroSync Care."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import websocket
from app.api.routes import sessions, source, system
from app.config import Settings, get_settings
from app.container import build_container
from app.errors import install_error_handlers
from app.services.acquisition_service import SourceFactory

log = logging.getLogger("neurosync")

DESCRIPTION = """
API local de **NeuroSync Care**, plataforma experimental de biofeedback EEG.

* No es un dispositivo médico: no diagnostica ni etiqueta emociones.
* Los datos con `source = SIMULATED` son sintéticos (DATOS SIMULADOS).
* Pensada para uso local: no exponer a Internet.
"""


def create_app(settings: Settings | None = None, emotiv_factory: SourceFactory | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = build_container(settings, emotiv_factory)
        app.state.container = container
        cleanup = container.sessions.startup_cleanup()
        log.info("Inicio: sesiones huérfanas cerradas=%s, descartadas sin consentimiento=%s", cleanup["aborted"], cleanup["purged"])
        try:
            yield
        finally:
            await container.acquisition.shutdown()
            container.recorder.flush()
            container.engine.dispose()

    app = FastAPI(title="NeuroSync Care API", version=__version__, description=DESCRIPTION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(app)
    app.include_router(system.router)
    app.include_router(source.router)
    app.include_router(sessions.router)
    app.include_router(websocket.router)
    return app


app = create_app()
