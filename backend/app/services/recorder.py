"""Registro de mediciones en SQLite con agregación por ventana.

Política de retención (ver docs/ARCHITECTURE.md): las muestras (pow a 8 Hz × sensores × bandas)
NO se guardan una a una. Se promedian los valores válidos por (ventana de ``bin_seconds``,
fuente, flujo, sensor, métrica) y se guarda una fila por ventana, junto con cuántas muestras
válidas y ausentes la formaron. Así la base se mantiene ligera sin inventar datos: las ventanas
sin muestras válidas se guardan como ausentes (``valid = False``), nunca se interpolan.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime

from app.database.core import SessionFactory, session_scope
from app.repositories.measurements import MeasurementRepository
from app.schemas.samples import SampleBatch

log = logging.getLogger(__name__)

_Key = tuple[float, int | None, str, str, str | None, str]


@dataclass
class _Bin:
    phase_id: int | None
    unit: str
    total: float = 0.0
    n_valid: int = 0
    n_missing: int = 0
    q_total: float = 0.0
    q_n: int = 0


class MeasurementRecorder:
    def __init__(self, session_factory: SessionFactory, bin_seconds: float = 1.0) -> None:
        self._factory = session_factory
        self._bin = bin_seconds
        self._bins: dict[_Key, _Bin] = {}
        self.session_id: int | None = None
        self.phase_id: int | None = None
        self.rows_written = 0

    @property
    def recording(self) -> bool:
        return self.session_id is not None

    def start(self, session_id: int) -> None:
        self.flush()
        self.session_id = session_id
        self.phase_id = None

    def set_phase(self, phase_id: int | None) -> None:
        self.flush()  # las ventanas abiertas pertenecen a la fase anterior
        self.phase_id = phase_id

    def stop(self) -> None:
        self.flush()
        self.session_id = None
        self.phase_id = None

    def add(self, batch: SampleBatch) -> None:
        if self.session_id is None:
            return
        newest = 0.0
        for s in batch.samples:
            start = math.floor(s.timestamp.timestamp() / self._bin) * self._bin
            newest = max(newest, start)
            key: _Key = (start, self.phase_id, s.source.value, s.stream.value, s.sensor, s.metric)
            b = self._bins.get(key)
            if b is None:
                b = self._bins[key] = _Bin(phase_id=self.phase_id, unit=s.unit)
            if s.valid and s.value is not None:
                b.total += s.value
                b.n_valid += 1
            else:
                b.n_missing += 1
            if s.quality is not None:
                b.q_total += s.quality
                b.q_n += 1
        # Escribe las ventanas ya cerradas (anteriores a la más reciente).
        self.flush(before=newest)

    def flush(self, before: float | None = None) -> int:
        if self.session_id is None:
            self._bins.clear()
            return 0
        if not self._bins:
            return 0
        keys = [k for k in self._bins if before is None or k[0] < before]
        if not keys:
            return 0
        rows = []
        for key in keys:
            b = self._bins.pop(key)
            start, _, source, stream, sensor, metric = key
            rows.append(
                {
                    "session_id": self.session_id,
                    "phase_id": b.phase_id,
                    "timestamp": datetime.fromtimestamp(start, UTC),
                    "source": source,
                    "stream": stream,
                    "sensor": sensor,
                    "metric": metric,
                    "value": round(b.total / b.n_valid, 6) if b.n_valid else None,
                    "unit": b.unit,
                    "valid": b.n_valid > 0,
                    "n_samples": b.n_valid,
                    "n_missing": b.n_missing,
                    "quality": round(b.q_total / b.q_n, 3) if b.q_n else None,
                }
            )
        try:
            with session_scope(self._factory) as db:
                MeasurementRepository(db).bulk_insert(rows)
            self.rows_written += len(rows)
        except Exception:
            log.exception("No se pudieron guardar %d mediciones", len(rows))
            return 0
        return len(rows)
