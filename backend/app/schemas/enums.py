"""Enumeraciones compartidas por todas las capas."""

from __future__ import annotations

from enum import StrEnum


class DataSource(StrEnum):
    SIMULATED = "SIMULATED"
    VIRTUAL_DEVICE = "VIRTUAL_DEVICE"
    REAL_EMOTIV = "REAL_EMOTIV"
    DISCONNECTED = "DISCONNECTED"


class Stream(StrEnum):
    """Nombres de flujo (coinciden con los de Cortex: dev, eq, pow, met)."""

    POW = "pow"
    EQ = "eq"
    DEV = "dev"
    MET = "met"


class ConnectionState(StrEnum):
    DISCONNECTED = "DISCONNECTED"  # no hay fuente activa
    CONNECTING = "CONNECTING"
    STREAMING = "STREAMING"  # recibiendo datos
    SIGNAL_LOST = "SIGNAL_LOST"  # la fuente existe pero dejó de entregar datos
    ERROR = "ERROR"


class IntegrationState(StrEnum):
    """Estado de la integración con EMOTIV Cortex (ver docs/EMOTIV_INTEGRATION.md)."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONNECTING = "CONNECTING"
    CORTEX_NOT_INSTALLED = "CORTEX_NOT_INSTALLED"
    CORTEX_UNAVAILABLE = "CORTEX_UNAVAILABLE"
    CREDENTIALS_MISSING = "CREDENTIALS_MISSING"
    CREDENTIALS_INVALID = "CREDENTIALS_INVALID"
    AUTHORIZATION_PENDING = "AUTHORIZATION_PENDING"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    STREAM_NOT_AUTHORIZED = "STREAM_NOT_AUTHORIZED"
    CONNECTED_STREAMING = "CONNECTED_STREAMING"
    COMMUNICATION_ERROR = "COMMUNICATION_ERROR"


class SimulatorScenario(StrEnum):
    NORMAL = "NORMAL"
    VARIABLE_POWER = "VARIABLE_POWER"
    POOR_QUALITY = "POOR_QUALITY"
    TEMPORARY_DISCONNECT = "TEMPORARY_DISCONNECT"
    NO_OPTIONAL_METRICS = "NO_OPTIONAL_METRICS"
    ACTIVITY_DEMO = "ACTIVITY_DEMO"


class SessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class PhaseKind(StrEnum):
    BASELINE = "BASELINE"  # referencia inicial
    MATH = "MATH"  # actividad cognitiva
    REGULATION = "REGULATION"  # autorregulación guiada


class PhaseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class ReportMoment(StrEnum):
    INITIAL = "INITIAL"
    POST_MATH = "POST_MATH"
    FINAL = "FINAL"
    OTHER = "OTHER"


class MathDifficulty(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class MathOperation(StrEnum):
    ADD = "ADD"
    SUBTRACT = "SUBTRACT"
    MULTIPLY = "MULTIPLY"


class AnswerResult(StrEnum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    SKIPPED = "SKIPPED"


BANDS: tuple[str, ...] = ("theta", "alpha", "low_beta", "high_beta", "gamma")
BAND_LABELS: dict[str, str] = {
    "theta": "Theta (4–8 Hz)",
    "alpha": "Alpha (8–12 Hz)",
    "low_beta": "Beta baja (12–16 Hz)",
    "high_beta": "Beta alta (16–25 Hz)",
    "gamma": "Gamma (25–45 Hz)",
}

