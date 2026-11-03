"""Esquemas de estadísticas descriptivas y comparaciones."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import PhaseKind, PhaseStatus, ReportMoment

DESCRIPTIVE_NOTE = (
    "Estadísticas puramente descriptivas de las muestras registradas. No son inferencias, "
    "diagnósticos ni medidas de estrés, emoción o capacidad. Las diferencias entre fases pueden "
    "deberse al azar, al movimiento, a la calidad del contacto y a otros factores."
)


class BandStats(BaseModel):
    band: str
    mean: float | None
    std: float | None
    minimum: float | None
    maximum: float | None
    n_valid_samples: int = Field(description="Muestras válidas agregadas en la ventana de persistencia.")
    n_valid_bins: int = Field(description="Instantes (ventanas de tiempo) con al menos un dato válido de la banda.")
    n_missing: int


class QualityStats(BaseModel):
    mean_overall_quality: float | None
    n_points: int


class PhaseStats(BaseModel):
    phase_id: int
    kind: PhaseKind
    detail: str | None
    status: PhaseStatus
    started_at: datetime
    ended_at: datetime | None
    planned_duration_s: float | None
    duration_s: float | None
    bands: list[BandStats]
    quality: QualityStats
    sources: list[str]
    sufficient: bool
    insufficient_reason: str | None = None


class MathStats(BaseModel):
    n_questions: int
    n_answered: int
    n_correct: int
    n_incorrect: int
    n_skipped: int
    accuracy_pct: float | None
    mean_response_time_ms: float | None
    median_response_time_ms: float | None
    duration_s: float | None


class SelfReportSummary(BaseModel):
    moment: ReportMoment
    tension: int
    difficulty: int | None
    comfort: int | None
    timestamp: datetime


class TensionChange(BaseModel):
    label: str
    from_moment: ReportMoment
    to_moment: ReportMoment
    change: int


class SessionSummary(BaseModel):
    session_id: int
    status: str
    data_source: str
    duration_s: float | None
    sources_present: list[str]
    mixed_sources: bool
    simulated_data: bool
    total_measurement_rows: int
    phases: list[PhaseStats]
    math: MathStats | None
    self_reports: list[SelfReportSummary]
    tension_changes: list[TensionChange]
    events_count: int
    note: str = DESCRIPTIVE_NOTE


class BandDelta(BaseModel):
    band: str
    mean_a: float | None
    mean_b: float | None
    absolute_change: float | None
    percent_change: float | None


class PhaseComparison(BaseModel):
    session_id: int
    phase_a: PhaseStats | None
    phase_b: PhaseStats | None
    available: bool
    reason: str | None
    deltas: list[BandDelta]
    note: str = DESCRIPTIVE_NOTE


class TimeseriesPoint(BaseModel):
    t: float = Field(description="Segundos desde el inicio de la sesión.")
    timestamp: datetime
    values: dict[str, float | None]
    phase_id: int | None


class TimeseriesOut(BaseModel):
    session_id: int
    bin_seconds: float
    bands: list[str]
    points: list[TimeseriesPoint]
    quality_points: list[TimeseriesPoint]
    unit: str | None
    simulated_data: bool
