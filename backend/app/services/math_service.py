"""Operaciones acotadas y respuestas vinculadas a su fase de origen."""
from __future__ import annotations

import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock

from sqlalchemy import func, select

from app.database.core import SessionFactory, session_scope
from app.errors import ConflictError, NotFoundError
from app.models.tables import CognitiveAnswerRow
from app.repositories.activities import ActivityRepository
from app.repositories.sessions import SessionRepository
from app.schemas.enums import AnswerResult, MathDifficulty, MathOperation, PhaseKind, SessionStatus
from app.schemas.samples import utcnow
from app.schemas.sessions import MathAnswerOut, MathAnswerRequest, MathQuestionOut, MathQuestionRequest
from app.services.protocol import PROTOCOL, phase_duration

QUESTION_TTL = timedelta(seconds=PROTOCOL.math.question_ttl_s)
MAX_PENDING = 256

_RANGES = {
    MathDifficulty.EASY: {"add": (2, 20), "sub": (2, 20), "mul": (2, 5)},
    MathDifficulty.MEDIUM: {"add": (10, 99), "sub": (10, 99), "mul": (2, 9)},
    MathDifficulty.HARD: {"add": (100, 999), "sub": (100, 999), "mul": (11, 19)},
}
_OPERATIONS = {
    MathDifficulty.EASY: [MathOperation.ADD, MathOperation.SUBTRACT],
    MathDifficulty.MEDIUM: [MathOperation.ADD, MathOperation.SUBTRACT, MathOperation.MULTIPLY],
    MathDifficulty.HARD: [MathOperation.ADD, MathOperation.SUBTRACT, MathOperation.MULTIPLY],
}


def generate_question(rng: random.Random, difficulty: MathDifficulty) -> tuple[str, MathOperation, int]:
    op = rng.choice(_OPERATIONS[difficulty])
    ranges = _RANGES[difficulty]
    if op == MathOperation.ADD:
        a, b = rng.randint(*ranges["add"]), rng.randint(*ranges["add"])
        return f"{a} + {b} = ?", op, a + b
    if op == MathOperation.SUBTRACT:
        a, b = sorted((rng.randint(*ranges["sub"]), rng.randint(*ranges["sub"])), reverse=True)
        return f"{a} - {b} = ?", op, a - b
    a, b = rng.randint(*ranges["mul"]), rng.randint(2, 9)
    return f"{a} × {b} = ?", op, a * b


@dataclass
class _Pending:
    session_id: int | None
    phase_id: int | None
    text: str
    operation: MathOperation
    difficulty: MathDifficulty
    expected: int
    issued_at: datetime
    expires_at: datetime
    number: int


class MathService:
    def __init__(self, session_factory: SessionFactory, seed: int | None = None, clock: Callable[[], datetime] = utcnow) -> None:
        self._factory = session_factory
        self._rng = random.Random(seed)
        self._clock = clock
        self._pending: dict[str, _Pending] = {}
        # La API es local y de un solo proceso; serializa solicitudes de distintos hilos.
        self._lock = RLock()

    def _purge(self, now: datetime) -> None:
        for qid in [key for key, value in self._pending.items() if now >= value.expires_at]:
            del self._pending[qid]

    @staticmethod
    def _math_phase(repo: SessionRepository, session_id: int, now: datetime):
        session = repo.get(session_id)
        if session is None:
            raise NotFoundError(f"La sesión {session_id} no existe.")
        if session.status != SessionStatus.ACTIVE:
            raise ConflictError(f"La sesión {session_id} ya finalizó.")
        phase = repo.active_phase(session_id)
        if phase is None or phase.kind != PhaseKind.MATH:
            raise ConflictError("Inicia la fase matemática antes de solicitar o responder operaciones.")
        duration = phase.planned_duration_s or phase_duration(PhaseKind.MATH, session.test_mode)
        deadline = phase.started_at + timedelta(seconds=duration)
        if now >= deadline:
            raise ConflictError("El tiempo de la actividad matemática terminó.")
        return phase, deadline

    @staticmethod
    def _out(qid: str, pending: _Pending) -> MathQuestionOut:
        return MathQuestionOut(
            question_id=qid, text=pending.text, operation=pending.operation,
            difficulty=pending.difficulty, issued_at=pending.issued_at,
            expires_at=pending.expires_at, question_number=pending.number,
            max_questions=PROTOCOL.math.max_questions, recorded=pending.session_id is not None,
        )

    def issue(self, req: MathQuestionRequest) -> MathQuestionOut:
        with self._lock:
            now = self._clock()
            self._purge(now)
            phase_id, number, expires_at = None, 1, now + QUESTION_TTL
            if req.session_id is not None:
                with session_scope(self._factory) as db:
                    phase, deadline = self._math_phase(SessionRepository(db), req.session_id, now)
                    phase_id = phase.id
                    count = db.scalar(select(func.count(CognitiveAnswerRow.id)).where(CognitiveAnswerRow.phase_id == phase_id)) or 0
                    if count >= PROTOCOL.math.max_questions:
                        raise ConflictError("Alcanzaste el límite de operaciones de esta fase.")
                    number, expires_at = count + 1, min(expires_at, deadline)
                # Reanudar o hacer doble clic no crea preguntas paralelas.
                for qid, pending in self._pending.items():
                    if pending.session_id == req.session_id and pending.phase_id == phase_id:
                        return self._out(qid, pending)
            if len(self._pending) >= MAX_PENDING:
                raise ConflictError("Hay demasiadas preguntas pendientes. Espera a que caduquen.")
            text, op, expected = generate_question(self._rng, req.difficulty)
            qid = uuid.uuid4().hex
            pending = _Pending(req.session_id, phase_id, text, op, req.difficulty, expected, now, expires_at, number)
            self._pending[qid] = pending
            return self._out(qid, pending)

    def answer(self, req: MathAnswerRequest) -> MathAnswerOut:
        with self._lock:
            now = self._clock()
            self._purge(now)
            pending = self._pending.get(req.question_id)
            if pending is None:
                raise NotFoundError("La pregunta no existe, ya fue respondida o expiró.")
            elapsed_ms = max(0, int((now - pending.issued_at).total_seconds() * 1000))
            result = AnswerResult.SKIPPED if req.answer is None else (
                AnswerResult.CORRECT if req.answer == pending.expected else AnswerResult.INCORRECT
            )
            recorded = False
            if pending.session_id is not None:
                with session_scope(self._factory) as db:
                    phase, _ = self._math_phase(SessionRepository(db), pending.session_id, now)
                    if phase.id != pending.phase_id:
                        raise ConflictError("Esta pregunta pertenece a una fase que ya terminó.")
                    ActivityRepository(db).add_answer(
                        session_id=pending.session_id, phase_id=pending.phase_id,
                        question_id=req.question_id, question_text=pending.text,
                        operation=pending.operation.value, difficulty=pending.difficulty.value,
                        given_answer=req.answer, expected_answer=pending.expected, result=result.value,
                        response_time_ms=elapsed_ms, timestamp=now,
                    )
                    recorded = True
            del self._pending[req.question_id]
            return MathAnswerOut(
                question_id=req.question_id, result=result, given_answer=req.answer,
                expected_answer=pending.expected, response_time_ms=elapsed_ms, recorded=recorded,
            )
