"""Contrato de datos normalizado (común al simulador y a EMOTIV Cortex)."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import DataSource, Stream

# Unidades. El simulador usa unidades arbitrarias: NO son microvoltios reales.
UNIT_POW_REAL = "uV^2/Hz"  # documentado por Cortex para el flujo 'pow'
UNIT_POW_SIMULATED = "u.a. (simulado)"
UNIT_QUALITY_SENSOR = "0-4"
UNIT_QUALITY_OVERALL = "0-100"
UNIT_SRQ = "0-1 (-1 = pérdida grave)"
UNIT_PERCENT = "%"
UNIT_SIGNAL = "0-1"
UNIT_DEMO = "0-1 (ficticio)"


def utcnow() -> datetime:
    return datetime.now(UTC)


class Sample(BaseModel):
    """Una medición puntual normalizada.

    * ``valid``: el valor existe y es un número finito.
    * ``active``: la muestra proviene de un flujo activo (False = marcador de hueco).
    * ``quality``: calidad del sensor (0-4) conocida en ese instante, si existe.
    """

    timestamp: datetime
    source: DataSource
    stream: Stream
    device_model: str | None = None
    sensor: str | None = None
    metric: str
    value: float | None = None
    unit: str
    quality: float | None = None
    active: bool = True
    valid: bool = True
    raw_label: str | None = None

    @model_validator(mode="after")
    def _check_value(self) -> Sample:
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)
        if self.value is None or not math.isfinite(self.value):
            self.value = None
            self.valid = False
            self.active = False
        return self


class SampleBatch(BaseModel):
    """Conjunto de muestras generadas en el mismo instante por una fuente."""

    timestamp: datetime
    source: DataSource
    device_model: str | None = None
    samples: list[Sample] = Field(default_factory=list)

