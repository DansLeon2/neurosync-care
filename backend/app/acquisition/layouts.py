"""Disposición de sensores por modelo de casco.

Los *nombres* de los sensores provienen de la documentación oficial de Cortex
(objeto ``headset``, campo ``sensors``, sistema internacional 10-20; ejemplos de
EPOC+/EPOC X e INSIGHT en la sección "Device information" de "Data sample object").

Las *coordenadas 2D* son posiciones aproximadas del sistema 10-20 en una proyección
superior estilizada (x: izquierda→derecha, y: atrás→frente, cabeza de radio 1).
Son implementación propia, solo para visualización: no son coordenadas medidas.
Cuando se confirme el modelo exacto del casco se debe validar contra su manual.
"""

from __future__ import annotations

from app.schemas.source import SensorLayout, SensorPosition

_NOTE = (
    "Nombres de sensores según la documentación oficial de EMOTIV Cortex (sistema 10-20). "
    "Posiciones 2D aproximadas, solo ilustrativas."
)

_POSITIONS: dict[str, tuple[float, float]] = {
    "AF3": (-0.27, 0.74),
    "AF4": (0.27, 0.74),
    "F7": (-0.72, 0.45),
    "F8": (0.72, 0.45),
    "F3": (-0.38, 0.42),
    "F4": (0.38, 0.42),
    "FC5": (-0.60, 0.20),
    "FC6": (0.60, 0.20),
    "T7": (-0.84, 0.0),
    "T8": (0.84, 0.0),
    "Pz": (0.0, -0.42),
    "P7": (-0.72, -0.45),
    "P8": (0.72, -0.45),
    "O1": (-0.28, -0.80),
    "O2": (0.28, -0.80),
}

EPOC_X_SENSORS = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
INSIGHT_SENSORS = ["AF3", "T7", "Pz", "T8", "AF4"]

DEFAULT_MODEL = "EPOCX"


def _layout(model: str, label: str, sensors: list[str]) -> SensorLayout:
    return SensorLayout(
        model=model,
        label=label,
        sensors=[SensorPosition(id=s, x=_POSITIONS[s][0], y=_POSITIONS[s][1]) for s in sensors],
        note=_NOTE,
    )


LAYOUTS: dict[str, SensorLayout] = {
    "EPOCX": _layout("EPOCX", "EPOC X / EPOC+ (14 canales)", EPOC_X_SENSORS),
    "INSIGHT": _layout("INSIGHT", "INSIGHT (5 canales)", INSIGHT_SENSORS),
}


def layout_for_sensors(sensors: list[str]) -> SensorLayout:
    """Layout para una lista de sensores anunciada por el dispositivo.

    Los sensores sin posición conocida se omiten del mapa (no se inventan coordenadas).
    """
    known = [s for s in sensors if s in _POSITIONS]
    return _layout("CUSTOM", "Disposición reportada por el dispositivo", known)

