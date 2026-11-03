"""Normalización de muestras de EMOTIV Cortex al contrato interno ``Sample``.

Implementación propia basada en el formato descrito en la documentación oficial
("Data sample object", https://emotiv.gitbook.io/cortex-api/data-subscription/data-sample-object):

* ``pow``: etiquetas ``SENSOR/BANDA`` (theta, alpha, betaL, betaH, gamma), uV^2/Hz.
* ``eq``: ``batteryPercent``, ``overall``, ``sampleRateQuality`` y la calidad (0-4) de cada sensor.
* ``dev``: ``["Battery","Signal",[sensores..., "OVERALL"],"BatteryPercent"]``.

Las posiciones NO se asumen: siempre se interpretan con los ``cols`` devueltos por ``subscribe``.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from app.schemas.enums import DataSource, Stream
from app.schemas.samples import (
    UNIT_PERCENT,
    UNIT_POW_REAL,
    UNIT_QUALITY_OVERALL,
    UNIT_QUALITY_SENSOR,
    UNIT_SIGNAL,
    UNIT_SRQ,
    Sample,
)

BAND_MAP = {
    "theta": "theta",
    "alpha": "alpha",
    "betaL": "low_beta",
    "betaH": "high_beta",
    "gamma": "gamma",
}


class MalformedSampleError(ValueError):
    """La muestra no es coherente con las columnas suscritas."""


def to_datetime(seconds: float | int | None) -> datetime:
    """El campo ``time`` de Cortex son segundos desde el epoch UTC."""
    if seconds is None or not isinstance(seconds, (int, float)) or not math.isfinite(seconds):
        return datetime.now(UTC)
    return datetime.fromtimestamp(float(seconds), UTC)


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    f = float(value)
    return f if math.isfinite(f) else None


def normalize_pow(
    cols: list[Any],
    values: list[Any],
    time_s: float | None,
    source: DataSource,
    device_model: str | None,
    qualities: dict[str, float] | None = None,
) -> list[Sample]:
    if len(cols) != len(values):
        raise MalformedSampleError(f"pow: {len(values)} valores para {len(cols)} columnas")
    ts = to_datetime(time_s)
    out: list[Sample] = []
    for col, raw in zip(cols, values, strict=True):
        if not isinstance(col, str) or "/" not in col:
            continue
        sensor, band = col.split("/", 1)
        metric = BAND_MAP.get(band)
        if metric is None:
            continue
        out.append(
            Sample(
                timestamp=ts,
                source=source,
                stream=Stream.POW,
                device_model=device_model,
                sensor=sensor,
                metric=metric,
                value=_num(raw),
                unit=UNIT_POW_REAL,
                quality=(qualities or {}).get(sensor),
                raw_label=col,
            )
        )
    return out


def normalize_eq(
    cols: list[Any], values: list[Any], time_s: float | None, source: DataSource, device_model: str | None
) -> list[Sample]:
    if len(cols) != len(values):
        raise MalformedSampleError(f"eq: {len(values)} valores para {len(cols)} columnas")
    ts = to_datetime(time_s)
    out: list[Sample] = []

    def add(metric: str, value: Any, unit: str, sensor: str | None, label: str) -> None:
        out.append(
            Sample(timestamp=ts, source=source, stream=Stream.EQ, device_model=device_model, sensor=sensor,
                   metric=metric, value=_num(value), unit=unit, raw_label=label)
        )

    for col, raw in zip(cols, values, strict=True):
        if not isinstance(col, str):
            continue
        if col == "batteryPercent":
            add("battery_percent", raw, UNIT_PERCENT, None, col)
        elif col == "overall":
            add("overall_quality", raw, UNIT_QUALITY_OVERALL, None, col)
        elif col == "sampleRateQuality":
            add("sample_rate_quality", raw, UNIT_SRQ, None, col)
        else:
            add("sensor_quality", raw, UNIT_QUALITY_SENSOR, col, col)
    return out


def normalize_dev(
    cols: list[Any], values: list[Any], time_s: float | None, source: DataSource, device_model: str | None
) -> list[Sample]:
    if len(cols) != len(values):
        raise MalformedSampleError(f"dev: {len(values)} valores para {len(cols)} columnas")
    ts = to_datetime(time_s)
    out: list[Sample] = []

    def add(metric: str, value: Any, unit: str, sensor: str | None, label: str) -> None:
        out.append(
            Sample(timestamp=ts, source=source, stream=Stream.DEV, device_model=device_model, sensor=sensor,
                   metric=metric, value=_num(value), unit=unit, raw_label=label)
        )

    for col, raw in zip(cols, values, strict=True):
        if isinstance(col, list):
            if not isinstance(raw, list) or len(raw) != len(col):
                raise MalformedSampleError("dev: la lista de contacto no coincide con sus columnas")
            for name, val in zip(col, raw, strict=True):
                if name == "OVERALL":
                    add("overall_contact_quality", val, UNIT_QUALITY_OVERALL, None, name)
                else:
                    add("contact_quality", val, UNIT_QUALITY_SENSOR, str(name), str(name))
        elif col == "Signal":
            add("signal", raw, UNIT_SIGNAL, None, col)
        elif col == "BatteryPercent":
            add("battery_percent", raw, UNIT_PERCENT, None, col)
        elif col == "Battery":
            add("battery_level", raw, "0-4", None, col)
    return out

