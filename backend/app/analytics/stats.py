"""Estadísticas descriptivas sobre los datos realmente almacenados.

Reglas:
* Solo se usan muestras válidas; nunca se rellenan ni interpolan huecos.
* Si no hay datos suficientes se informa (``sufficient=False`` + motivo), no se inventa nada.
* Son estadísticas descriptivas, no inferencias ni medidas clínicas.
"""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import pandas as pd

from app.models.tables import CognitiveAnswerRow, PhaseRow, SelfReportRow
from app.schemas.analytics import (
    BandDelta,
    BandStats,
    MathStats,
    PhaseComparison,
    PhaseStats,
    QualityStats,
    SelfReportSummary,
    TensionChange,
    TimeseriesOut,
    TimeseriesPoint,
)
from app.schemas.enums import BANDS, AnswerResult, ReportMoment


def _f(x: float | None) -> float | None:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return None
    return round(float(x), 6)


def _duration(start: datetime, end: datetime | None) -> float | None:
    return round((end - start).total_seconds(), 2) if end else None


def band_stats(pow_phase: pd.DataFrame, band: str) -> BandStats:
    rows = pow_phase[pow_phase["metric"] == band] if not pow_phase.empty else pow_phase
    if rows.empty:
        return BandStats(band=band, mean=None, std=None, minimum=None, maximum=None, n_valid_samples=0, n_valid_bins=0, n_missing=0)
    good = rows[rows["valid"].astype(bool) & rows["value"].notna()]
    n_missing = int(rows["n_missing"].sum())
    if good.empty:
        return BandStats(band=band, mean=None, std=None, minimum=None, maximum=None, n_valid_samples=0, n_valid_bins=0, n_missing=n_missing)
    return BandStats(
        band=band,
        mean=_f(good["value"].mean()),
        std=_f(good["value"].std(ddof=1)) if len(good) > 1 else None,
        minimum=_f(good["value"].min()),
        maximum=_f(good["value"].max()),
        n_valid_samples=int(good["n_samples"].sum()),
        n_valid_bins=int(good["timestamp"].nunique()),  # ventanas de tiempo con dato válido
        n_missing=n_missing,
    )


def phase_stats(phase: PhaseRow, df: pd.DataFrame, min_valid_bins: int) -> PhaseStats:
    sub = df[df["phase_id"] == phase.id] if not df.empty else df
    pow_rows = sub[sub["stream"] == "pow"] if not sub.empty else sub
    bands = [band_stats(pow_rows, b) for b in BANDS]

    q_rows = sub[(sub["stream"] == "eq") & (sub["metric"] == "overall_quality") & sub["valid"].astype(bool)] if not sub.empty else sub
    quality = QualityStats(
        mean_overall_quality=_f(q_rows["value"].mean()) if not q_rows.empty else None,
        n_points=int(len(q_rows)),
    )
    sources = sorted(sub["source"].unique().tolist()) if not sub.empty else []

    min_bins = min((b.n_valid_bins for b in bands), default=0)
    sufficient = min_bins >= min_valid_bins
    reason = None
    if not sufficient:
        reason = (
            "No hay datos EEG registrados en esta fase."
            if min_bins == 0 and not any(b.n_valid_samples for b in bands)
            else f"Información insuficiente: se requieren al menos {min_valid_bins} instantes válidos por banda (hay {min_bins})."
        )
    return PhaseStats(
        phase_id=phase.id,
        kind=phase.kind,  # type: ignore[arg-type]
        detail=phase.detail,
        status=phase.status,  # type: ignore[arg-type]
        started_at=phase.started_at,
        ended_at=phase.ended_at,
        planned_duration_s=phase.planned_duration_s,
        duration_s=_duration(phase.started_at, phase.ended_at),
        bands=bands,
        quality=quality,
        sources=sources,
        sufficient=sufficient,
        insufficient_reason=reason,
    )


def math_stats(answers: list[CognitiveAnswerRow]) -> MathStats | None:
    if not answers:
        return None
    n = len(answers)
    correct = sum(a.result == AnswerResult.CORRECT for a in answers)
    incorrect = sum(a.result == AnswerResult.INCORRECT for a in answers)
    skipped = sum(a.result == AnswerResult.SKIPPED for a in answers)
    times = [a.response_time_ms for a in answers if a.result != AnswerResult.SKIPPED]
    span = (answers[-1].timestamp - answers[0].timestamp).total_seconds() if n > 1 else None
    return MathStats(
        n_questions=n,
        n_answered=correct + incorrect,
        n_correct=correct,
        n_incorrect=incorrect,
        n_skipped=skipped,
        accuracy_pct=round(100.0 * correct / n, 1),
        mean_response_time_ms=_f(float(np.mean(times))) if times else None,
        median_response_time_ms=_f(float(np.median(times))) if times else None,
        duration_s=_f(span),
    )


def self_report_summaries(rows: list[SelfReportRow]) -> list[SelfReportSummary]:
    return [
        SelfReportSummary(moment=r.moment, tension=r.tension, difficulty=r.difficulty, comfort=r.comfort, timestamp=r.timestamp)  # type: ignore[arg-type]
        for r in rows
    ]


def tension_changes(rows: list[SelfReportRow]) -> list[TensionChange]:
    """Cambios de tensión *subjetiva* entre momentos (último reporte de cada momento)."""
    by_moment: dict[str, int] = {}
    for r in rows:
        by_moment[r.moment] = r.tension
    pairs = [
        (ReportMoment.INITIAL, ReportMoment.POST_MATH, "Inicial → tras actividad matemática"),
        (ReportMoment.POST_MATH, ReportMoment.FINAL, "Tras actividad matemática → final"),
        (ReportMoment.INITIAL, ReportMoment.FINAL, "Inicial → final"),
    ]
    out = []
    for a, b, label in pairs:
        if a in by_moment and b in by_moment:
            out.append(TensionChange(label=label, from_moment=a, to_moment=b, change=by_moment[b] - by_moment[a]))
    return out


def compare_phases(session_id: int, a: PhaseStats | None, b: PhaseStats | None) -> PhaseComparison:
    if a is None or b is None:
        missing = "la fase A" if a is None else "la fase B"
        return PhaseComparison(
            session_id=session_id, phase_a=a, phase_b=b, available=False,
            reason=f"No existe {missing} en esta sesión.", deltas=[],
        )
    if not (a.sufficient and b.sufficient):
        why = a.insufficient_reason if not a.sufficient else b.insufficient_reason
        return PhaseComparison(
            session_id=session_id, phase_a=a, phase_b=b, available=False,
            reason=f"Comparación no disponible. {why}", deltas=[],
        )
    deltas = []
    for ba, bb in zip(a.bands, b.bands, strict=True):
        if ba.mean is None or bb.mean is None:
            deltas.append(BandDelta(band=ba.band, mean_a=ba.mean, mean_b=bb.mean, absolute_change=None, percent_change=None))
            continue
        diff = bb.mean - ba.mean
        pct = (diff / ba.mean * 100.0) if ba.mean != 0 else None
        deltas.append(BandDelta(band=ba.band, mean_a=ba.mean, mean_b=bb.mean, absolute_change=_f(diff), percent_change=_f(pct)))
    return PhaseComparison(session_id=session_id, phase_a=a, phase_b=b, available=True, reason=None, deltas=deltas)


def timeseries(df: pd.DataFrame, started_at: datetime, bin_seconds: float, simulated: bool) -> TimeseriesOut:
    """Media por instante entre sensores para cada banda (solo valores válidos)."""
    points: list[TimeseriesPoint] = []
    q_points: list[TimeseriesPoint] = []
    unit = None
    if not df.empty:
        pow_rows = df[(df["stream"] == "pow") & df["valid"].astype(bool) & df["value"].notna()]
        if not pow_rows.empty:
            unit = str(pow_rows["unit"].iloc[0])
            grouped = pow_rows.groupby(["timestamp", "metric"])["value"].mean().unstack("metric")
            phase_by_ts = pow_rows.groupby("timestamp")["phase_id"].first()
            for ts, row in grouped.iterrows():
                pid = phase_by_ts.loc[ts]
                points.append(
                    TimeseriesPoint(
                        t=round((ts.to_pydatetime() - started_at).total_seconds(), 2),
                        timestamp=ts.to_pydatetime(),
                        values={b: (_f(row[b]) if b in row and pd.notna(row[b]) else None) for b in BANDS},
                        phase_id=None if pd.isna(pid) else int(pid),
                    )
                )
        q = df[(df["stream"] == "eq") & (df["metric"] == "overall_quality") & df["valid"].astype(bool) & df["value"].notna()]
        for _, r in q.iterrows():
            q_points.append(
                TimeseriesPoint(
                    t=round((r["timestamp"].to_pydatetime() - started_at).total_seconds(), 2),
                    timestamp=r["timestamp"].to_pydatetime(),
                    values={"overall": _f(r["value"])},
                    phase_id=None if pd.isna(r["phase_id"]) else int(r["phase_id"]),
                )
            )
    return TimeseriesOut(
        session_id=0, bin_seconds=bin_seconds, bands=list(BANDS), points=points, quality_points=q_points, unit=unit,
        simulated_data=simulated,
    )

