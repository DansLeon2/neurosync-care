"""Contratos del piloto de comprensión: no se ejecuta código del participante."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CodingTask(BaseModel):
    id: str
    title: str
    difficulty: str
    prompt: str
    code: str
    options: list[str]
    max_attempts: int = 3
    criteria: str = "Seleccionar la respuesta correcta; no se ejecutan pruebas de software."


class CodingAnswerRequest(BaseModel):
    session_id: int = Field(gt=0)
    task_id: str = Field(min_length=1, max_length=40)
    choice: int = Field(strict=True, ge=0, le=3)


class CodingAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: int
    phase_id: int
    task_id: str
    difficulty: str
    choice: int
    correct: bool
    attempt: int
    elapsed_ms: int
    timestamp: datetime


class CodingStats(BaseModel):
    n_attempts: int
    n_tasks: int
    n_completed: int
    n_incomplete: int
    first_correct_ms: int | None
