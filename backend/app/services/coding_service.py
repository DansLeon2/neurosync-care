"""Piloto de lectura de código, con corrección determinista y tiempo del servidor."""
from collections.abc import Callable
from datetime import datetime, timedelta
from threading import RLock
from sqlalchemy import select
from app.database.core import SessionFactory, session_scope
from app.errors import ConflictError, NotFoundError
from app.models.tables import CodingAnswerRow
from app.repositories.sessions import SessionRepository
from app.schemas.coding import CodingAnswerOut, CodingAnswerRequest, CodingStats, CodingTask
from app.schemas.enums import PhaseKind, SessionStatus
from app.schemas.samples import utcnow
from app.services.protocol import phase_duration

_TASKS = [
    (CodingTask(id="sum-even-v1", title="Comprender un recorrido", difficulty="EASY",
        prompt="¿Qué valor devuelve esta función para [1, 2, 3, 4]?",
        code="def sumar_pares(valores):\n    total = 0\n    for valor in valores:\n        if valor % 2 == 0:\n            total += valor\n    return total",
        options=["10", "6", "4", "2"]), 1),
    (CodingTask(id="off-by-one-v1", title="Detectar un error de límite", difficulty="MEDIUM",
        prompt="Se quiere sumar TODOS los elementos. ¿Qué cambio corrige el recorrido?",
        code="def sumar(valores):\n    total = 0\n    for i in range(len(valores) - 1):\n        total += valores[i]\n    return total",
        options=["Usar range(len(valores))", "Iniciar total en 1", "Mover return al interior del for", "Usar valores[i - 1]"]), 0),
]


def tasks() -> list[CodingTask]:
    return [task for task, _ in _TASKS]


def coding_rows(db, session_id: int) -> list[CodingAnswerRow]:
    return list(db.scalars(select(CodingAnswerRow).where(CodingAnswerRow.session_id == session_id).order_by(CodingAnswerRow.id)))


def coding_stats(rows: list[CodingAnswerRow], n_tasks: int = 0) -> CodingStats | None:
    if not rows and not n_tasks:
        return None
    correct = [row for row in rows if row.correct]
    total = max(n_tasks, len({r.phase_id for r in rows}))
    completed = len({r.phase_id for r in correct})
    return CodingStats(n_attempts=len(rows), n_tasks=total, n_completed=completed,
        n_incomplete=total-completed, first_correct_ms=correct[0].elapsed_ms if correct else None)


class CodingService:
    def __init__(self, factory: SessionFactory, clock: Callable[[], datetime] = utcnow):
        self._factory, self._clock, self._lock = factory, clock, RLock()

    def answer(self, request: CodingAnswerRequest) -> CodingAnswerOut:
        entry = next((item for item in _TASKS if item[0].id == request.task_id), None)
        if entry is None:
            raise NotFoundError("La tarea de código no existe.")
        task, expected = entry
        with self._lock, session_scope(self._factory) as db:
            repo = SessionRepository(db)
            session = repo.get(request.session_id)
            if session is None:
                raise NotFoundError("La sesión no existe.")
            phase = repo.active_phase(session.id)
            if session.status != SessionStatus.ACTIVE or phase is None or phase.kind != PhaseKind.CODING:
                raise ConflictError("Se requiere una fase CODING activa.")
            if phase.detail != task.id:
                raise ConflictError("La tarea no corresponde a esta fase.")
            now = self._clock()
            duration = phase.planned_duration_s or phase_duration(PhaseKind.CODING, session.test_mode)
            if now >= phase.started_at + timedelta(seconds=duration):
                raise ConflictError("El tiempo de la tarea terminó.")
            previous = [row for row in coding_rows(db, session.id) if row.phase_id == phase.id]
            if len(previous) >= task.max_attempts or any(row.correct for row in previous):
                raise ConflictError("La tarea ya está resuelta o alcanzó el límite de intentos.")
            row = CodingAnswerRow(session_id=session.id, phase_id=phase.id, task_id=task.id,
                difficulty=task.difficulty, choice=request.choice, correct=request.choice == expected,
                attempt=len(previous) + 1, elapsed_ms=max(0, int((now - phase.started_at).total_seconds() * 1000)), timestamp=now)
            db.add(row)
            db.flush()
            return CodingAnswerOut.model_validate(row)
