"""Esquemas de sesiones, fases, autoevaluaciones y actividad matemática."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    AnswerResult,
    DataSource,
    MathDifficulty,
    MathOperation,
    PhaseKind,
    PhaseStatus,
    ReportMoment,
    SessionStatus,
)


class SessionCreate(BaseModel):
    consent_storage: bool = Field(
        default=False,
        description="True = el participante autoriza guardar los resultados localmente. "
        "False = la sesión se descarta al terminar (no aparece en el historial).",
    )
    test_mode: bool = Field(default=False, description="Modo de prueba con duraciones cortas (solo desarrollo).")


class PhaseCreate(BaseModel):
    kind: PhaseKind
    planned_duration_s: float | None = Field(default=None, gt=0, le=3600)
    detail: str | None = Field(default=None, max_length=40)


class PhaseEnd(BaseModel):
    status: Literal["COMPLETED", "ABORTED"] = "COMPLETED"


class SessionFinish(BaseModel):
    status: Literal["COMPLETED", "ABORTED"] = "COMPLETED"


class PhaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    kind: PhaseKind
    detail: str | None
    planned_duration_s: float | None
    started_at: datetime
    ended_at: datetime | None
    status: PhaseStatus


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    ended_at: datetime | None
    data_source: DataSource
    status: SessionStatus
    consent_storage: bool
    device_model: str | None
    test_mode: bool
    duration_s: float | None = None
    phases: list[PhaseOut] = Field(default_factory=list)


class SessionListItem(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None
    duration_s: float | None
    data_source: DataSource
    status: SessionStatus
    test_mode: bool
    activities: list[PhaseKind]
    tension_initial: int | None
    tension_final: int | None
    math_total: int
    math_correct: int


class SelfReportCreate(BaseModel):
    moment: ReportMoment = ReportMoment.OTHER
    tension: int = Field(ge=0, le=10, description="¿Cuánta tensión percibes? 0 = ninguna, 10 = máxima.")
    difficulty: int | None = Field(default=None, ge=0, le=10)
    comfort: int | None = Field(default=None, ge=0, le=10)
    note: str | None = Field(default=None, max_length=300)
    phase_id: int | None = None


class SelfReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    phase_id: int | None
    moment: ReportMoment
    tension: int
    difficulty: int | None
    comfort: int | None
    note: str | None
    timestamp: datetime


class MathQuestionRequest(BaseModel):
    difficulty: MathDifficulty = MathDifficulty.EASY
    session_id: int | None = None


class MathQuestionOut(BaseModel):
    question_id: str
    text: str
    operation: MathOperation
    difficulty: MathDifficulty
    issued_at: datetime
    expires_at: datetime
    question_number: int
    max_questions: int
    recorded: bool = Field(description="True si la respuesta se registrará en una sesión activa.")


class MathAnswerRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=64)
    answer: int | None = Field(default=None, strict=True, ge=-9999, le=9999, description="Entero de -9999 a 9999; null = omitida.")


class MathAnswerOut(BaseModel):
    question_id: str
    result: AnswerResult
    given_answer: int | None
    expected_answer: int
    response_time_ms: int
    recorded: bool


class CognitiveAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    phase_id: int | None
    question_id: str
    question_text: str
    operation: MathOperation
    difficulty: MathDifficulty
    given_answer: int | None
    expected_answer: int
    result: AnswerResult
    response_time_ms: int
    timestamp: datetime


class DeviceEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int | None
    event: str
    detail: str | None
    source: str | None
    timestamp: datetime


class SessionDetail(BaseModel):
    session: SessionOut
    self_reports: list[SelfReportOut]
    answers: list[CognitiveAnswerOut]
    events: list[DeviceEventOut]


class ProtocolPhaseDef(BaseModel):
    key: str
    label: str
    description: str
    default_duration_s: int
    test_duration_s: int
    kind: PhaseKind | None


class MathPolicy(BaseModel):
    max_questions: int = 20
    question_ttl_s: int = 120
    answer_min: int = -9999
    answer_max: int = 9999


class ProtocolOut(BaseModel):
    math: MathPolicy = Field(default_factory=MathPolicy)
    phases: list[ProtocolPhaseDef]
    disclaimer: str

