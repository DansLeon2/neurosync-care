"""Orquestación de sesiones, fases y autoevaluaciones."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.database.core import SessionFactory, session_scope
from app.errors import ConflictError, NotFoundError
from app.models.tables import PhaseRow, SessionRow
from app.repositories.activities import ActivityRepository
from app.repositories.sessions import SessionRepository
from app.schemas.enums import PhaseKind, PhaseStatus, SessionStatus
from app.schemas.samples import utcnow
from app.schemas.sessions import (
    PhaseCreate,
    PhaseOut,
    SelfReportCreate,
    SelfReportOut,
    SessionCreate,
    SessionOut,
)
from app.services.acquisition_service import AcquisitionService
from app.services.hub import StreamHub
from app.services.pipeline import Pipeline
from app.services.protocol import phase_duration
from app.services.recorder import MeasurementRecorder


def session_out(row: SessionRow, now: datetime | None = None) -> SessionOut:
    end = row.ended_at or (now or utcnow())
    return SessionOut(
        id=row.id,
        started_at=row.started_at,
        ended_at=row.ended_at,
        data_source=row.data_source,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        consent_storage=row.consent_storage,
        device_model=row.device_model,
        test_mode=row.test_mode,
        duration_s=round((end - row.started_at).total_seconds(), 2),
        phases=[PhaseOut.model_validate(p) for p in row.phases],
    )


class SessionService:
    def __init__(
        self,
        session_factory: SessionFactory,
        recorder: MeasurementRecorder,
        pipeline: Pipeline,
        acquisition: AcquisitionService,
        hub: StreamHub,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._factory = session_factory
        self._recorder = recorder
        self._pipeline = pipeline
        self._acq = acquisition
        self._hub = hub
        self._clock = clock

    # ---- helpers
    def _announce(self, event: str, row: SessionRow, extra: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"type": "session", "event": event, "session": session_out(row).model_dump(mode="json")}
        if extra:
            payload.update(extra)
        self._hub.broadcast(payload)

    @staticmethod
    def _get(repo: SessionRepository, session_id: int) -> SessionRow:
        row = repo.get(session_id)
        if row is None:
            raise NotFoundError(f"La sesión {session_id} no existe.")
        return row

    def _get_active(self, repo: SessionRepository, session_id: int) -> SessionRow:
        row = self._get(repo, session_id)
        if row.status != SessionStatus.ACTIVE:
            raise ConflictError(f"La sesión {session_id} ya finalizó.")
        return row

    # ---- sesiones
    def start(self, req: SessionCreate) -> SessionOut:
        with session_scope(self._factory) as db:
            repo = SessionRepository(db)
            active = repo.get_active()
            if active is not None:
                raise ConflictError(f"Ya hay una sesión activa (#{active.id}). Finalízala antes de iniciar otra.")
            status = self._acq.status()
            row = repo.create(
                source=self._acq.current_source.value,
                consent=req.consent_storage,
                device_model=status.device.model if status.device else None,
                test_mode=req.test_mode,
                now=self._clock(),
            )
            ActivityRepository(db).add_event(
                session_id=row.id, event="SESSION_STARTED", detail=f"Fuente: {row.data_source}", source=row.data_source,
                timestamp=self._clock(),
            )
            out = session_out(row)
        self._recorder.start(out.id)
        self._announce("started", self._reload(out.id))
        return out

    def _reload(self, session_id: int) -> SessionRow:
        with session_scope(self._factory) as db:
            return self._get(SessionRepository(db), session_id)

    def active(self) -> SessionOut | None:
        with session_scope(self._factory) as db:
            row = SessionRepository(db).get_active()
            return session_out(row) if row else None

    def get(self, session_id: int) -> SessionOut:
        with session_scope(self._factory) as db:
            return session_out(self._get(SessionRepository(db), session_id))

    def finish(self, session_id: int, status: SessionStatus) -> SessionOut:
        # Se vacían las ventanas pendientes ANTES de abrir la transacción (SQLite admite un solo escritor).
        if self._recorder.session_id == session_id:
            self._recorder.flush()
        with session_scope(self._factory) as db:
            repo = SessionRepository(db)
            row = self._get_active(repo, session_id)
            now = self._clock()
            phase = repo.active_phase(session_id)
            if phase:
                repo.end_phase(phase, PhaseStatus.ABORTED if status == SessionStatus.ABORTED else PhaseStatus.COMPLETED, now)
            if self._recorder.session_id == session_id:
                self._recorder.stop()
            self._acq.set_phase_context(None)
            repo.finish(row, status, now)
            ActivityRepository(db).add_event(
                session_id=session_id, event=f"SESSION_{status.value}", detail=None, source=row.data_source, timestamp=now
            )
            out = session_out(row)
        self._announce("finished", self._reload(session_id))
        return out

    def delete(self, session_id: int) -> None:
        with session_scope(self._factory) as db:
            repo = SessionRepository(db)
            row = self._get(repo, session_id)
            if row.status == SessionStatus.ACTIVE:
                raise ConflictError("No se puede borrar una sesión activa. Finalízala primero.")
            repo.delete(session_id)

    def delete_all(self) -> int:
        with session_scope(self._factory) as db:
            return SessionRepository(db).delete_all()

    # ---- fases
    def start_phase(self, session_id: int, req: PhaseCreate) -> PhaseOut:
        with session_scope(self._factory) as db:
            repo = SessionRepository(db)
            session = self._get_active(repo, session_id)
            now = self._clock()
            current = repo.active_phase(session_id)
            if current:
                raise ConflictError("Termina la fase actual antes de iniciar otra.")
            duration = req.planned_duration_s or phase_duration(req.kind, session.test_mode)
            if req.kind == PhaseKind.MATH and duration > phase_duration(PhaseKind.MATH):
                raise ConflictError(f"La fase matemática admite como máximo {phase_duration(PhaseKind.MATH)} segundos.")
            phase = repo.add_phase(session_id, kind=req.kind.value, detail=req.detail, planned=duration, now=now)
            out = PhaseOut.model_validate(phase)
        self._recorder.set_phase(out.id)
        self._acq.set_phase_context(req.kind)
        self._announce("phase_started", self._reload(session_id), {"phase": out.model_dump(mode="json")})
        return out

    def end_phase(self, session_id: int, phase_id: int, status: PhaseStatus) -> PhaseOut:
        with session_scope(self._factory) as db:
            repo = SessionRepository(db)
            self._get(repo, session_id)
            phase = repo.get_phase(phase_id)
            if phase is None or phase.session_id != session_id:
                raise NotFoundError(f"La fase {phase_id} no existe en la sesión {session_id}.")
            if phase.status == PhaseStatus.ACTIVE:
                repo.end_phase(phase, status, self._clock())
            out = PhaseOut.model_validate(phase)
        if self._recorder.phase_id == phase_id:
            self._recorder.set_phase(None)
            self._acq.set_phase_context(None)
        self._announce("phase_ended", self._reload(session_id), {"phase": out.model_dump(mode="json")})
        return out

    # ---- autoevaluaciones
    def add_self_report(self, session_id: int, req: SelfReportCreate) -> SelfReportOut:
        with session_scope(self._factory) as db:
            repo = SessionRepository(db)
            self._get_active(repo, session_id)
            phase_id = req.phase_id
            if phase_id is not None:
                phase: PhaseRow | None = repo.get_phase(phase_id)
                if phase is None or phase.session_id != session_id:
                    raise NotFoundError(f"La fase {phase_id} no existe en la sesión {session_id}.")
            else:
                active = repo.active_phase(session_id)
                phase_id = active.id if active else None
            row = ActivityRepository(db).add_self_report(
                session_id=session_id, phase_id=phase_id, moment=req.moment.value, tension=req.tension,
                difficulty=req.difficulty, comfort=req.comfort, note=req.note, timestamp=self._clock(),
            )
            return SelfReportOut.model_validate(row)

    def startup_cleanup(self) -> dict[str, int]:
        """Al iniciar: cierra sesiones huérfanas y descarta las que no tenían consentimiento."""
        with session_scope(self._factory) as db:
            repo = SessionRepository(db)
            aborted = repo.abort_orphans(self._clock())
            purged = repo.purge_ephemeral()
        return {"aborted": aborted, "purged": purged}

    def discard_if_ephemeral(self, session_id: int) -> bool:
        """Descarta una sesión sin consentimiento tras mostrar sus resultados."""
        with session_scope(self._factory) as db:
            repo = SessionRepository(db)
            row = repo.get(session_id)
            if row is None or row.consent_storage or row.status == SessionStatus.ACTIVE:
                return False
            return repo.delete(session_id)
