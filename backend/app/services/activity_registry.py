"""Extensiones de actividad; MATH conserva sus fases y contratos históricos."""
from app.schemas.enums import ActivityKind, PhaseKind, ReportMoment

ACTIVITIES = {
    ActivityKind.MATH: {
        "id": "MATH", "label": "Operaciones", "phase": PhaseKind.MATH,
        "report_moment": ReportMoment.POST_MATH, "duration_s": 120, "test_duration_s": 8,
    },
    ActivityKind.CODING: {
        "id": "CODING", "label": "Lectura de código · piloto", "phase": PhaseKind.CODING,
        "report_moment": ReportMoment.POST_CODING, "duration_s": 120, "test_duration_s": 20,
    },
}
