"""Acceso a datos: sesiones y fases."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.tables import PhaseRow, SessionRow
from app.schemas.enums import PhaseStatus, SessionStatus


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- sesiones
    def create(self, *, source: str, consent: bool, device_model: str | None, test_mode: bool, now: datetime) -> SessionRow:
        row = SessionRow(
            started_at=now,
            data_source=source,
            status=SessionStatus.ACTIVE,
            consent_storage=consent,
            device_model=device_model,
            test_mode=test_mode,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, session_id: int) -> SessionRow | None:
        stmt = select(SessionRow).options(selectinload(SessionRow.phases)).where(SessionRow.id == session_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active(self) -> SessionRow | None:
        stmt = (
            select(SessionRow)
            .options(selectinload(SessionRow.phases))
            .where(SessionRow.status == SessionStatus.ACTIVE)
            .order_by(SessionRow.started_at.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def list_saved(self) -> list[SessionRow]:
        """Historial: solo sesiones con consentimiento de almacenamiento."""
        stmt = (
            select(SessionRow)
            .options(selectinload(SessionRow.phases))
            .where(SessionRow.consent_storage.is_(True))
            .order_by(SessionRow.started_at.desc())
        )
        return list(self.db.execute(stmt).scalars())

    def finish(self, row: SessionRow, status: SessionStatus, ended_at: datetime) -> SessionRow:
        row.status = status
        row.ended_at = ended_at
        self.db.flush()
        return row

    def delete(self, session_id: int) -> bool:
        res = self.db.execute(delete(SessionRow).where(SessionRow.id == session_id))
        return bool(res.rowcount)

    def delete_all(self) -> int:
        res = self.db.execute(delete(SessionRow).where(SessionRow.status != SessionStatus.ACTIVE))
        return int(res.rowcount or 0)

    def purge_ephemeral(self, *, include_active: bool = False) -> int:
        stmt = delete(SessionRow).where(SessionRow.consent_storage.is_(False))
        if not include_active:
            stmt = stmt.where(SessionRow.status != SessionStatus.ACTIVE)
        return int(self.db.execute(stmt).rowcount or 0)

    def abort_orphans(self, now: datetime) -> int:
        """Sesiones que quedaron ACTIVE por un cierre inesperado del backend."""
        rows = self.db.execute(select(SessionRow).where(SessionRow.status == SessionStatus.ACTIVE)).scalars().all()
        for row in rows:
            row.status = SessionStatus.ABORTED
            row.ended_at = now
            for ph in self.db.execute(select(PhaseRow).where(PhaseRow.session_id == row.id, PhaseRow.status == PhaseStatus.ACTIVE)).scalars():
                ph.status = PhaseStatus.ABORTED
                ph.ended_at = now
        self.db.flush()
        return len(rows)

    def count(self) -> int:
        return int(self.db.execute(select(func.count(SessionRow.id))).scalar_one())

    # ---- fases
    def add_phase(
        self, session_id: int, *, kind: str, detail: str | None, planned: float | None, now: datetime
    ) -> PhaseRow:
        row = PhaseRow(
            session_id=session_id, kind=kind, detail=detail, planned_duration_s=planned, started_at=now,
            status=PhaseStatus.ACTIVE,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_phase(self, phase_id: int) -> PhaseRow | None:
        return self.db.get(PhaseRow, phase_id)

    def active_phase(self, session_id: int) -> PhaseRow | None:
        stmt = select(PhaseRow).where(PhaseRow.session_id == session_id, PhaseRow.status == PhaseStatus.ACTIVE)
        return self.db.execute(stmt.order_by(PhaseRow.started_at.desc())).scalars().first()

    def end_phase(self, row: PhaseRow, status: PhaseStatus, ended_at: datetime) -> PhaseRow:
        row.status = status
        row.ended_at = ended_at
        self.db.flush()
        return row

