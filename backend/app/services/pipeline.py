"""Pipeline único de datos: fuente → estado más reciente → registro SQLite → WebSocket.

Tanto el simulador como EMOTIV Cortex entregan aquí el mismo contrato (``SampleBatch``).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.database.core import SessionFactory, session_scope
from app.repositories.activities import ActivityRepository
from app.schemas.enums import ConnectionState, DataSource, Stream
from app.schemas.samples import SampleBatch, utcnow
from app.schemas.source import SourceStatus
from app.services.hub import StreamHub
from app.services.recorder import MeasurementRecorder

log = logging.getLogger(__name__)


class LatestState:
    """Último valor conocido de cada magnitud, para construir fotogramas de interfaz."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.source: DataSource = DataSource.DISCONNECTED
        self.device_model: str | None = None
        self.pow: dict[str, dict[str, float | None]] = {}
        self.pow_unit: str | None = None
        self.quality: dict[str, float | None] = {}
        self.contact: dict[str, float | None] = {}
        self.overall_quality: float | None = None
        self.sample_rate_quality: float | None = None
        self.battery_percent: float | None = None
        self.signal: float | None = None
        self.met: dict[str, float | None] = {}
        self.timestamp: datetime | None = None
        self.seq = 0

    def update(self, batch: SampleBatch) -> None:
        self.source = batch.source
        self.device_model = batch.device_model or self.device_model
        self.timestamp = batch.timestamp
        self.seq += 1
        for s in batch.samples:
            if s.stream == Stream.POW and s.sensor:
                self.pow.setdefault(s.sensor, {})[s.metric] = s.value
                self.pow_unit = s.unit
            elif s.stream == Stream.EQ:
                if s.metric == "sensor_quality" and s.sensor:
                    self.quality[s.sensor] = s.value
                elif s.metric == "overall_quality":
                    self.overall_quality = s.value
                elif s.metric == "sample_rate_quality":
                    self.sample_rate_quality = s.value
                elif s.metric == "battery_percent":
                    self.battery_percent = s.value
            elif s.stream == Stream.DEV:
                if s.metric == "contact_quality" and s.sensor:
                    self.contact[s.sensor] = s.value
                elif s.metric == "battery_percent":
                    self.battery_percent = s.value
                elif s.metric == "signal":
                    self.signal = s.value
            elif s.stream == Stream.MET:
                self.met[s.metric] = s.value

    def frame(self) -> dict[str, Any] | None:
        if self.timestamp is None:
            return None
        return {
            "type": "frame",
            "seq": self.seq,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source.value,
            "simulated": self.source == DataSource.SIMULATED,
            "device_model": self.device_model,
            "pow": self.pow,
            "pow_unit": self.pow_unit,
            "quality": self.quality,
            "contact": self.contact,
            "overall_quality": self.overall_quality,
            "sample_rate_quality": self.sample_rate_quality,
            "battery_percent": self.battery_percent,
            "signal": self.signal,
            "met": self.met or None,
        }


class Pipeline:
    def __init__(self, hub: StreamHub, recorder: MeasurementRecorder, session_factory: SessionFactory) -> None:
        self.hub = hub
        self.recorder = recorder
        self._factory = session_factory
        self.state = LatestState()
        self.status = SourceStatus()
        self.samples_received = 0

    async def ingest(self, batch: SampleBatch) -> None:
        if batch.source != self.state.source:
            self.state.reset()
        self.state.update(batch)
        self.samples_received += len(batch.samples)
        self.recorder.add(batch)
        frame = self.state.frame()
        if frame:
            self.hub.broadcast(frame)

    async def status_changed(self, status: SourceStatus) -> None:
        previous = self.status
        self.status = status
        if status.source != previous.source:
            self.state.reset()
        self.hub.broadcast({"type": "status", "status": status.model_dump(mode="json")})
        if (status.connection, status.integration_state) != (previous.connection, previous.integration_state):
            self.log_event(status.connection.value, status.message, status.source.value)

    def log_event(self, event: str, detail: str | None, source: str | None) -> None:
        """Registra un evento de dispositivo (asociado a la sesión activa, si existe)."""
        try:
            with session_scope(self._factory) as db:
                ActivityRepository(db).add_event(
                    session_id=self.recorder.session_id, event=event, detail=detail, source=source, timestamp=utcnow()
                )
        except Exception:
            log.exception("No se pudo registrar el evento %s", event)

    def reset_for_source_stop(self) -> None:
        self.state.reset()
        self.status = SourceStatus(connection=ConnectionState.DISCONNECTED)

