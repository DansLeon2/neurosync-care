"""Interfaz común de las fuentes de datos (simulador y EMOTIV Cortex)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from app.schemas.enums import DataSource
from app.schemas.samples import SampleBatch
from app.schemas.source import SourceStatus


class SampleSink(Protocol):
    """Destino de las muestras: el mismo pipeline para cualquier fuente."""

    async def ingest(self, batch: SampleBatch) -> None: ...

    async def status_changed(self, status: SourceStatus) -> None: ...


class DataSourceAdapter(ABC):
    source: DataSource

    def __init__(self, sink: SampleSink) -> None:
        self._sink = sink

    @abstractmethod
    async def start(self) -> None:
        """Inicia la adquisición (no bloquea: lanza tareas internas)."""

    @abstractmethod
    async def stop(self) -> None:
        """Detiene la adquisición y libera recursos."""

    @abstractmethod
    def status(self) -> SourceStatus:
        """Estado actual de la fuente."""

