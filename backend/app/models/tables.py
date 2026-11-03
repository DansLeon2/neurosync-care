"""Tablas SQLite (SQLAlchemy 2.0).

Política de privacidad: no se almacena ningún dato personal identificable.
Política de muestreo de ``measurements``: ver docs/ARCHITECTURE.md (agregación por ventana).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.core import Base, UTCDateTime


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    data_source: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(12), default="ACTIVE")
    consent_storage: Mapped[bool] = mapped_column(Boolean, default=False)
    device_model: Mapped[str | None] = mapped_column(String(40), nullable=True)
    test_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    phases: Mapped[list[PhaseRow]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True, order_by="PhaseRow.started_at"
    )


class PhaseRow(Base):
    __tablename__ = "session_phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    detail: Mapped[str | None] = mapped_column(String(40), nullable=True)  # p. ej. BREATHING / ATTENTION / EASY
    planned_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="ACTIVE")

    session: Mapped[SessionRow] = relationship(back_populates="phases")


class MeasurementRow(Base):
    """Medición agregada: media de las muestras válidas de una ventana (por defecto 1 s)."""

    __tablename__ = "measurements"
    __table_args__ = (
        Index("ix_meas_session_phase", "session_id", "phase_id"),
        Index("ix_meas_session_ts", "session_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    phase_id: Mapped[int | None] = mapped_column(ForeignKey("session_phases.id", ondelete="SET NULL"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime)
    source: Mapped[str] = mapped_column(String(20))
    stream: Mapped[str] = mapped_column(String(8))
    sensor: Mapped[str | None] = mapped_column(String(10), nullable=True)
    metric: Mapped[str] = mapped_column(String(32))
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(40))
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    n_samples: Mapped[int] = mapped_column(Integer, default=1)  # muestras válidas agregadas
    n_missing: Mapped[int] = mapped_column(Integer, default=0)  # muestras ausentes/inválidas en la ventana
    quality: Mapped[float | None] = mapped_column(Float, nullable=True)


class SelfReportRow(Base):
    __tablename__ = "self_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    phase_id: Mapped[int | None] = mapped_column(ForeignKey("session_phases.id", ondelete="SET NULL"), nullable=True)
    moment: Mapped[str] = mapped_column(String(12))
    tension: Mapped[int] = mapped_column(Integer)  # 0-10, subjetiva
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comfort: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime)


class CognitiveAnswerRow(Base):
    __tablename__ = "cognitive_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    phase_id: Mapped[int | None] = mapped_column(ForeignKey("session_phases.id", ondelete="SET NULL"), nullable=True)
    question_id: Mapped[str] = mapped_column(String(40))
    question_text: Mapped[str] = mapped_column(String(80))
    operation: Mapped[str] = mapped_column(String(10))
    difficulty: Mapped[str] = mapped_column(String(10))
    given_answer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_answer: Mapped[int] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String(10))
    response_time_ms: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime)


class DeviceEventRow(Base):
    __tablename__ = "device_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime)

