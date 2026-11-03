"""Protocolo experimental guiado (definición única; el frontend la consume vía API)."""

from __future__ import annotations

from app.schemas.enums import PhaseKind
from app.schemas.sessions import ProtocolOut, ProtocolPhaseDef

DISCLAIMER = (
    "NeuroSync Care es una plataforma experimental de demostración. No es un dispositivo médico, "
    "no diagnostica ni evalúa estados emocionales o capacidades, y no garantiza reducción del estrés. "
    "Puedes detener cualquier actividad cuando lo necesites."
)

PROTOCOL = ProtocolOut(
    disclaimer=DISCLAIMER,
    phases=[
        ProtocolPhaseDef(
            key="intro", label="Inicio", kind=None, default_duration_s=0, test_duration_s=0,
            description="Información de la actividad, consentimiento de almacenamiento local y fuente de datos.",
        ),
        ProtocolPhaseDef(
            key="baseline", label="Referencia inicial", kind=PhaseKind.BASELINE, default_duration_s=120, test_duration_s=8,
            description="Permanece sentado/a cómodamente mientras se registra la información disponible.",
        ),
        ProtocolPhaseDef(
            key="math", label="Actividad cognitiva", kind=PhaseKind.MATH, default_duration_s=120, test_duration_s=8,
            description="Resuelve operaciones matemáticas sencillas a tu ritmo.",
        ),
        ProtocolPhaseDef(
            key="self_report_mid", label="Autoevaluación", kind=None, default_duration_s=0, test_duration_s=0,
            description="Registra tu tensión percibida y la dificultad de la actividad.",
        ),
        ProtocolPhaseDef(
            key="regulation", label="Autorregulación guiada", kind=PhaseKind.REGULATION, default_duration_s=180, test_duration_s=10,
            description="Respiración cómoda o atención al entorno. Puedes detenerte cuando quieras.",
        ),
        ProtocolPhaseDef(
            key="self_report_final", label="Evaluación final", kind=None, default_duration_s=0, test_duration_s=0,
            description="Registra de nuevo tu tensión percibida y qué tan cómoda fue la sesión.",
        ),
        ProtocolPhaseDef(
            key="results", label="Resultados", kind=None, default_duration_s=0, test_duration_s=0,
            description="Resumen descriptivo de la sesión.",
        ),
    ],
)



def phase_duration(kind: PhaseKind, test_mode: bool = False) -> int:
    """Duración compartida por los servicios y publicada en /api/protocol."""
    phase = next(p for p in PROTOCOL.phases if p.kind == kind)
    return phase.test_duration_s if test_mode else phase.default_duration_s
