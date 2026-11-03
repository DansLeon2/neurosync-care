"""Gestión de la fuente de datos activa (simulador / EMOTIV)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.acquisition.base import DataSourceAdapter
from app.acquisition.emotiv import EmotivCortexSource
from app.acquisition.simulator import SimulatedSource
from app.config import Settings
from app.errors import ConflictError
from app.schemas.enums import ConnectionState, DataSource, IntegrationState, PhaseKind
from app.schemas.source import SimulatorConfig, SimulatorConfigUpdate, SourceStatus
from app.services.pipeline import Pipeline

log = logging.getLogger(__name__)

SourceFactory = Callable[[DataSource], DataSourceAdapter]


class AcquisitionService:
    def __init__(self, settings: Settings, pipeline: Pipeline, emotiv_factory: SourceFactory | None = None) -> None:
        self._settings = settings
        self._pipeline = pipeline
        self._emotiv_factory = emotiv_factory
        self._source: DataSourceAdapter | None = None
        self.simulator_config = SimulatorConfig(seed=settings.simulator_seed)
        self._phase_context: PhaseKind | None = None

    @property
    def current_source(self) -> DataSource:
        return self._source.source if self._source else DataSource.DISCONNECTED

    @property
    def simulator(self) -> SimulatedSource | None:
        return self._source if isinstance(self._source, SimulatedSource) else None

    def status(self) -> SourceStatus:
        return self._source.status() if self._source else SourceStatus()

    def _build(self, target: DataSource) -> DataSourceAdapter:
        if target == DataSource.SIMULATED:
            src = SimulatedSource(self._pipeline, self.simulator_config.model_copy())
            src.set_phase_context(self._phase_context)
            return src
        if self._emotiv_factory:
            return self._emotiv_factory(target)
        return EmotivCortexSource(self._pipeline, self._settings, source=target)

    async def select(self, target: DataSource, *, force: bool = False) -> SourceStatus:
        active_session = self._pipeline.recorder.session_id
        if active_session is not None and target != self.current_source and not force:
            raise ConflictError(
                "Hay una sesión activa: cambiar la fuente mezclaría datos de distinto origen. "
                "Finaliza la sesión o confirma el cambio explícitamente."
            )
        previous = self.current_source
        if self._source is not None:
            await self._source.stop()
            self._source = None
            self._pipeline.reset_for_source_stop()
        if active_session is not None and target != previous:
            self._pipeline.log_event("SOURCE_CHANGED", f"{previous.value} → {target.value}", target.value)
        if target == DataSource.DISCONNECTED:
            await self._pipeline.status_changed(SourceStatus(connection=ConnectionState.DISCONNECTED))
            return self.status()
        self._source = self._build(target)
        await self._source.start()
        if target != DataSource.SIMULATED:
            # Espera breve para que la respuesta HTTP ya incluya el resultado inicial (p. ej. credenciales ausentes).
            for _ in range(40):
                if self._source.status().integration_state != IntegrationState.CONNECTING:
                    break
                await asyncio.sleep(0.05)
        return self.status()

    async def shutdown(self) -> None:
        if self._source:
            await self._source.stop()
            self._source = None

    # --- simulador
    def update_simulator(self, update: SimulatorConfigUpdate) -> SimulatorConfig:
        data = self.simulator_config.model_dump()
        data.update({k: v for k, v in update.model_dump().items() if v is not None})
        self.simulator_config = SimulatorConfig(**data)
        if self.simulator:
            self.simulator.set_config(self.simulator_config.model_copy())
        return self.simulator_config

    def _require_simulator(self) -> SimulatedSource:
        if self.simulator is None:
            raise ConflictError("El simulador no está activo.")
        return self.simulator

    async def simulate_disconnect(self, duration_s: float | None) -> SourceStatus:
        sim = self._require_simulator()
        sim.simulate_disconnect(duration_s)
        await self._pipeline.status_changed(sim.status())
        return sim.status()

    async def reconnect(self) -> SourceStatus:
        sim = self._require_simulator()
        sim.reconnect()
        await self._pipeline.status_changed(sim.status())
        return sim.status()

    def set_phase_context(self, kind: PhaseKind | None) -> None:
        self._phase_context = kind
        if self.simulator:
            self.simulator.set_phase_context(kind)
