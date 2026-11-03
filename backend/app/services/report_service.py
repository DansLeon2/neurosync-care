"""Reportes de sesión: historial, resumen estadístico, comparaciones, series y exportación CSV."""

from __future__ import annotations

import csv
import io

import pandas as pd

from app.analytics import stats
from app.config import Settings
from app.database.core import SessionFactory, session_scope
from app.errors import NotFoundError
from app.models.tables import PhaseRow, SessionRow
from app.repositories.activities import ActivityRepository
from app.repositories.measurements import MeasurementRepository
from app.repositories.sessions import SessionRepository
from app.schemas.analytics import PhaseComparison, PhaseStats, SessionSummary, TimeseriesOut
from app.schemas.enums import AnswerResult, DataSource, PhaseKind, ReportMoment
from app.schemas.samples import utcnow
from app.schemas.sessions import (
    CognitiveAnswerOut,
    DeviceEventOut,
    SelfReportOut,
    SessionDetail,
    SessionListItem,
)
from app.services.session_service import session_out

EXPORT_DATASETS = ("measurements", "answers", "self_reports", "summary")


class ReportService:
    def __init__(self, session_factory: SessionFactory, settings: Settings) -> None:
        self._factory = session_factory
        self._settings = settings

    # ---- historial
    def list_items(self) -> list[SessionListItem]:
        items: list[SessionListItem] = []
        with session_scope(self._factory) as db:
            activities = ActivityRepository(db)
            for row in SessionRepository(db).list_saved():
                reports = activities.self_reports(row.id)
                by_moment = {r.moment: r.tension for r in reports}
                answers = activities.answers(row.id)
                out = session_out(row)
                items.append(
                    SessionListItem(
                        id=row.id,
                        started_at=row.started_at,
                        ended_at=row.ended_at,
                        duration_s=out.duration_s,
                        data_source=row.data_source,  # type: ignore[arg-type]
                        status=row.status,  # type: ignore[arg-type]
                        test_mode=row.test_mode,
                        activities=sorted({p.kind for p in row.phases}, key=lambda k: list(PhaseKind).index(PhaseKind(k))),  # type: ignore[arg-type]
                        tension_initial=by_moment.get(ReportMoment.INITIAL),
                        tension_final=by_moment.get(ReportMoment.FINAL),
                        math_total=len(answers),
                        math_correct=sum(a.result == AnswerResult.CORRECT for a in answers),
                    )
                )
        return items

    def detail(self, session_id: int) -> SessionDetail:
        with session_scope(self._factory) as db:
            row = self._session(db, session_id)
            act = ActivityRepository(db)
            return SessionDetail(
                session=session_out(row),
                self_reports=[SelfReportOut.model_validate(r) for r in act.self_reports(session_id)],
                answers=[CognitiveAnswerOut.model_validate(a) for a in act.answers(session_id)],
                events=[DeviceEventOut.model_validate(e) for e in act.events(session_id)],
            )

    @staticmethod
    def _session(db, session_id: int) -> SessionRow:  # type: ignore[no-untyped-def]
        row = SessionRepository(db).get(session_id)
        if row is None:
            raise NotFoundError(f"La sesión {session_id} no existe.")
        return row

    # ---- estadísticas
    def summary(self, session_id: int) -> SessionSummary:
        with session_scope(self._factory) as db:
            row = self._session(db, session_id)
            df = MeasurementRepository(db).dataframe(session_id)
            act = ActivityRepository(db)
            reports = act.self_reports(session_id)
            answers = act.answers(session_id)
            events = act.events(session_id)
            phases = [stats.phase_stats(p, df, self._settings.min_valid_bins) for p in row.phases]
            sources = sorted(df["source"].unique().tolist()) if not df.empty else []
            out = session_out(row)
            return SessionSummary(
                session_id=session_id,
                status=row.status,
                data_source=row.data_source,
                duration_s=out.duration_s,
                sources_present=sources,
                mixed_sources=len(sources) > 1,
                simulated_data=DataSource.SIMULATED.value in sources or row.data_source == DataSource.SIMULATED.value,
                total_measurement_rows=int(len(df)),
                phases=phases,
                math=stats.math_stats(answers),
                self_reports=stats.self_report_summaries(reports),
                tension_changes=stats.tension_changes(reports),
                events_count=len(events),
            )

    @staticmethod
    def _pick_phase(phases: list[PhaseRow], ref: str) -> PhaseRow | None:
        if ref.isdigit():
            return next((p for p in phases if p.id == int(ref)), None)
        matches = [p for p in phases if p.kind == ref.upper()]
        return matches[-1] if matches else None

    def compare(self, session_id: int, a: str, b: str) -> PhaseComparison:
        with session_scope(self._factory) as db:
            row = self._session(db, session_id)
            df = MeasurementRepository(db).dataframe(session_id)
            pa, pb = self._pick_phase(row.phases, a), self._pick_phase(row.phases, b)
            min_bins = self._settings.min_valid_bins
            sa: PhaseStats | None = stats.phase_stats(pa, df, min_bins) if pa else None
            sb: PhaseStats | None = stats.phase_stats(pb, df, min_bins) if pb else None
            return stats.compare_phases(session_id, sa, sb)

    def timeseries(self, session_id: int) -> TimeseriesOut:
        with session_scope(self._factory) as db:
            row = self._session(db, session_id)
            df = MeasurementRepository(db).dataframe(session_id)
            simulated = row.data_source == DataSource.SIMULATED.value or (
                not df.empty and (df["source"] == DataSource.SIMULATED.value).any()
            )
            ts = stats.timeseries(df, row.started_at, self._settings.persist_bin_seconds, bool(simulated))
            ts.session_id = session_id
            return ts

    # ---- exportación
    def export_csv(self, session_id: int, dataset: str) -> str:
        if dataset not in EXPORT_DATASETS:
            raise NotFoundError(f"Conjunto de datos desconocido: {dataset}. Opciones: {', '.join(EXPORT_DATASETS)}")
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        with session_scope(self._factory) as db:
            row = self._session(db, session_id)
            phase_kind = {p.id: p.kind for p in row.phases}
            if dataset == "measurements":
                df = MeasurementRepository(db).dataframe(session_id)
                w.writerow(["session_id", "phase_id", "phase_kind", "timestamp_utc", "source", "stream", "sensor", "metric",
                            "value", "unit", "valid", "n_samples", "n_missing", "quality"])
                for r in df.itertuples(index=False):
                    pid = None if pd.isna(r.phase_id) else int(r.phase_id)
                    w.writerow([session_id, pid, phase_kind.get(pid, "") if pid is not None else "", r.timestamp.isoformat(),
                                r.source, r.stream, r.sensor or "", r.metric, "" if pd.isna(r.value) else r.value, r.unit,
                                int(bool(r.valid)), r.n_samples, r.n_missing, "" if pd.isna(r.quality) else r.quality])
            elif dataset == "answers":
                w.writerow(["session_id", "phase_id", "question_id", "question", "operation", "difficulty", "given_answer",
                            "expected_answer", "result", "response_time_ms", "timestamp_utc"])
                for a in ActivityRepository(db).answers(session_id):
                    w.writerow([session_id, a.phase_id or "", a.question_id, a.question_text, a.operation, a.difficulty,
                                "" if a.given_answer is None else a.given_answer, a.expected_answer, a.result,
                                a.response_time_ms, a.timestamp.isoformat()])
            elif dataset == "self_reports":
                w.writerow(["session_id", "phase_id", "moment", "tension_0_10", "difficulty_0_10", "comfort_0_10", "note", "timestamp_utc"])
                for r in ActivityRepository(db).self_reports(session_id):
                    w.writerow([session_id, r.phase_id or "", r.moment, r.tension, "" if r.difficulty is None else r.difficulty,
                                "" if r.comfort is None else r.comfort, r.note or "", r.timestamp.isoformat()])
        if dataset == "summary":
            summary = self.summary(session_id)
            w.writerow(["session_id", "phase_id", "phase_kind", "band", "mean", "std", "min", "max", "n_valid_samples",
                        "n_valid_bins", "n_missing", "duration_s", "sufficient", "sources"])
            for p in summary.phases:
                for b in p.bands:
                    w.writerow([session_id, p.phase_id, p.kind.value, b.band, _blank(b.mean), _blank(b.std), _blank(b.minimum),
                                _blank(b.maximum), b.n_valid_samples, b.n_valid_bins, b.n_missing, _blank(p.duration_s),
                                int(p.sufficient), "|".join(p.sources)])
        return buf.getvalue()

    def export_filename(self, session_id: int, dataset: str) -> str:
        return f"neurosync_sesion{session_id}_{dataset}_{utcnow():%Y%m%d}.csv"


def _blank(v: float | None) -> float | str:
    return "" if v is None else v

