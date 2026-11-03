"""Composición de dependencias de la aplicación (sin singletons globales)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from app.config import Settings
from app.database.core import SessionFactory, init_db, make_engine, make_session_factory
from app.services.acquisition_service import AcquisitionService, SourceFactory
from app.services.hub import StreamHub
from app.services.math_service import MathService
from app.services.pipeline import Pipeline
from app.services.recorder import MeasurementRecorder
from app.services.report_service import ReportService
from app.services.session_service import SessionService


@dataclass
class Container:
    settings: Settings
    engine: Engine
    session_factory: SessionFactory
    hub: StreamHub
    recorder: MeasurementRecorder
    pipeline: Pipeline
    acquisition: AcquisitionService
    sessions: SessionService
    math: MathService
    reports: ReportService


def build_container(settings: Settings, emotiv_factory: SourceFactory | None = None) -> Container:
    engine = make_engine(settings.database_url)
    init_db(engine)
    factory = make_session_factory(engine)
    hub = StreamHub()
    recorder = MeasurementRecorder(factory, settings.persist_bin_seconds)
    pipeline = Pipeline(hub, recorder, factory)
    acquisition = AcquisitionService(settings, pipeline, emotiv_factory)
    return Container(
        settings=settings,
        engine=engine,
        session_factory=factory,
        hub=hub,
        recorder=recorder,
        pipeline=pipeline,
        acquisition=acquisition,
        sessions=SessionService(factory, recorder, pipeline, acquisition, hub),
        math=MathService(factory),
        reports=ReportService(factory, settings),
    )

