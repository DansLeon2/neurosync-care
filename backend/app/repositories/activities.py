"""Acceso a datos: autoevaluaciones, respuestas cognitivas y eventos de dispositivo."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import CognitiveAnswerRow, DeviceEventRow, SelfReportRow


class ActivityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- autoevaluaciones
    def add_self_report(self, **fields) -> SelfReportRow:  # type: ignore[no-untyped-def]
        row = SelfReportRow(**fields)
        self.db.add(row)
        self.db.flush()
        return row

    def self_reports(self, session_id: int) -> list[SelfReportRow]:
        stmt = select(SelfReportRow).where(SelfReportRow.session_id == session_id).order_by(SelfReportRow.timestamp, SelfReportRow.id)
        return list(self.db.execute(stmt).scalars())

    # ---- respuestas cognitivas
    def add_answer(self, **fields) -> CognitiveAnswerRow:  # type: ignore[no-untyped-def]
        row = CognitiveAnswerRow(**fields)
        self.db.add(row)
        self.db.flush()
        return row

    def answers(self, session_id: int) -> list[CognitiveAnswerRow]:
        stmt = select(CognitiveAnswerRow).where(CognitiveAnswerRow.session_id == session_id).order_by(
            CognitiveAnswerRow.timestamp, CognitiveAnswerRow.id
        )
        return list(self.db.execute(stmt).scalars())

    # ---- eventos
    def add_event(self, *, session_id: int | None, event: str, detail: str | None, source: str | None, timestamp: datetime) -> DeviceEventRow:
        row = DeviceEventRow(session_id=session_id, event=event, detail=detail, source=source, timestamp=timestamp)
        self.db.add(row)
        self.db.flush()
        return row

    def events(self, session_id: int) -> list[DeviceEventRow]:
        stmt = select(DeviceEventRow).where(DeviceEventRow.session_id == session_id).order_by(DeviceEventRow.timestamp, DeviceEventRow.id)
        return list(self.db.execute(stmt).scalars())

