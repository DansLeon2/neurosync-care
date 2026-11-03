"""Sesiones, fases, autoevaluaciones, actividad matemática, estadísticas y exportación."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_container
from app.container import Container
from app.schemas.analytics import PhaseComparison, SessionSummary, TimeseriesOut
from app.schemas.enums import PhaseStatus, SessionStatus
from app.schemas.sessions import (
    MathAnswerOut,
    MathAnswerRequest,
    MathQuestionOut,
    MathQuestionRequest,
    PhaseCreate,
    PhaseEnd,
    PhaseOut,
    SelfReportCreate,
    SelfReportOut,
    SessionCreate,
    SessionDetail,
    SessionFinish,
    SessionListItem,
    SessionOut,
)

router = APIRouter(prefix="/api", tags=["Sesiones"])
Ctx = Annotated[Container, Depends(get_container)]


@router.post("/sessions", response_model=SessionOut, status_code=201, summary="Inicia una sesión")
def start_session(req: SessionCreate, ctx: Ctx) -> SessionOut:
    return ctx.sessions.start(req)


@router.get("/sessions/active", response_model=SessionOut | None, summary="Sesión activa (si existe)")
def active_session(ctx: Ctx) -> SessionOut | None:
    return ctx.sessions.active()


@router.get("/sessions", response_model=list[SessionListItem], summary="Historial de sesiones guardadas")
def list_sessions(ctx: Ctx) -> list[SessionListItem]:
    return ctx.reports.list_items()


@router.delete("/sessions", summary="Borra todas las sesiones almacenadas (no activas)")
def delete_all_sessions(ctx: Ctx) -> dict[str, int]:
    return {"deleted": ctx.sessions.delete_all()}


@router.get("/sessions/{session_id}", response_model=SessionDetail, summary="Detalle de una sesión")
def session_detail(session_id: int, ctx: Ctx) -> SessionDetail:
    return ctx.reports.detail(session_id)


@router.post("/sessions/{session_id}/finish", response_model=SessionOut, summary="Finaliza una sesión")
def finish_session(session_id: int, ctx: Ctx, req: SessionFinish | None = None) -> SessionOut:
    status = SessionStatus((req or SessionFinish()).status)
    return ctx.sessions.finish(session_id, status)


@router.delete("/sessions/{session_id}", status_code=204, summary="Elimina una sesión")
def delete_session(session_id: int, ctx: Ctx) -> Response:
    ctx.sessions.delete(session_id)
    return Response(status_code=204)


@router.post("/sessions/{session_id}/discard", summary="Descarta la sesión si no tenía consentimiento de almacenamiento")
def discard_session(session_id: int, ctx: Ctx) -> dict[str, bool]:
    return {"discarded": ctx.sessions.discard_if_ephemeral(session_id)}


# --- fases
@router.post("/sessions/{session_id}/phases", response_model=PhaseOut, status_code=201, summary="Inicia una fase")
def start_phase(session_id: int, req: PhaseCreate, ctx: Ctx) -> PhaseOut:
    return ctx.sessions.start_phase(session_id, req)


@router.post("/sessions/{session_id}/phases/{phase_id}/end", response_model=PhaseOut, summary="Finaliza una fase")
def end_phase(session_id: int, phase_id: int, ctx: Ctx, req: PhaseEnd | None = None) -> PhaseOut:
    status = PhaseStatus((req or PhaseEnd()).status)
    return ctx.sessions.end_phase(session_id, phase_id, status)


# --- autoevaluaciones
@router.post("/sessions/{session_id}/self-reports", response_model=SelfReportOut, status_code=201, summary="Registra una autoevaluación")
def add_self_report(session_id: int, req: SelfReportCreate, ctx: Ctx) -> SelfReportOut:
    return ctx.sessions.add_self_report(session_id, req)


# --- actividad matemática (la sesión es opcional: modo práctica)
@router.post("/math/questions", response_model=MathQuestionOut, summary="Genera una operación matemática")
def math_question(req: MathQuestionRequest, ctx: Ctx) -> MathQuestionOut:
    return ctx.math.issue(req)


@router.post("/math/answers", response_model=MathAnswerOut, summary="Evalúa y registra una respuesta")
def math_answer(req: MathAnswerRequest, ctx: Ctx) -> MathAnswerOut:
    return ctx.math.answer(req)


# --- estadísticas
@router.get("/sessions/{session_id}/summary", response_model=SessionSummary, summary="Resumen estadístico descriptivo")
def session_summary(session_id: int, ctx: Ctx) -> SessionSummary:
    return ctx.reports.summary(session_id)


@router.get("/sessions/{session_id}/compare", response_model=PhaseComparison, summary="Comparación descriptiva entre dos fases")
def compare_phases(
    session_id: int,
    ctx: Ctx,
    a: Annotated[str, Query(description="BASELINE | MATH | REGULATION o id de fase")] = "BASELINE",
    b: Annotated[str, Query(description="BASELINE | MATH | REGULATION o id de fase")] = "MATH",
) -> PhaseComparison:
    return ctx.reports.compare(session_id, a, b)


@router.get("/sessions/{session_id}/timeseries", response_model=TimeseriesOut, summary="Serie temporal agregada")
def session_timeseries(session_id: int, ctx: Ctx) -> TimeseriesOut:
    return ctx.reports.timeseries(session_id)


@router.get("/sessions/{session_id}/export.csv", summary="Exportación CSV", response_class=Response)
def export_csv(
    session_id: int,
    ctx: Ctx,
    dataset: Annotated[str, Query(description="measurements | answers | self_reports | summary")] = "measurements",
) -> Response:
    content = ctx.reports.export_csv(session_id, dataset)
    headers: dict[str, Any] = {"Content-Disposition": f'attachment; filename="{ctx.reports.export_filename(session_id, dataset)}"'}
    return Response(content="\ufeff" + content, media_type="text/csv; charset=utf-8", headers=headers)

