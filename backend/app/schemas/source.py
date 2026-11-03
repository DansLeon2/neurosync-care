"""Esquemas del estado de la fuente de datos y de las capacidades disponibles."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.enums import ConnectionState, DataSource, IntegrationState, SimulatorScenario

CapabilityState = Literal["available", "unavailable", "not_authorized", "unknown", "disabled"]


class DeviceInfo(BaseModel):
    id: str | None = None
    model: str | None = None
    is_virtual: bool | None = None
    connected_by: str | None = None
    firmware: str | None = None
    sensors: list[str] = Field(default_factory=list)
    battery_percent: float | None = None


class StreamCapability(BaseModel):
    stream: str
    label: str
    state: CapabilityState
    rate_hz: float | None = None
    note: str | None = None


class SourceStatus(BaseModel):
    source: DataSource = DataSource.DISCONNECTED
    simulated: bool = False
    connection: ConnectionState = ConnectionState.DISCONNECTED
    integration_state: IntegrationState = IntegrationState.NOT_APPLICABLE
    message: str = "Sin fuente de datos activa."
    device: DeviceInfo | None = None
    scenario: SimulatorScenario | None = None
    last_sample_at: datetime | None = None
    streams: list[StreamCapability] = Field(default_factory=list)


class SourceSelectRequest(BaseModel):
    source: DataSource
    force: bool = Field(
        default=False,
        description="Permite cambiar de fuente aunque haya una sesión activa (queda registrado como evento).",
    )


class SimulatorConfig(BaseModel):
    scenario: SimulatorScenario = SimulatorScenario.NORMAL
    seed: int = 42
    poor_sensors: list[str] = Field(default_factory=list)


class SimulatorConfigUpdate(BaseModel):
    scenario: SimulatorScenario | None = None
    seed: int | None = None
    poor_sensors: list[str] | None = None


class SimulatorDisconnectRequest(BaseModel):
    duration_s: float | None = Field(
        default=5.0, gt=0, le=600, description="Segundos de desconexión simulada; null = hasta reconectar."
    )


class SensorPosition(BaseModel):
    id: str
    x: float
    y: float


class SensorLayout(BaseModel):
    model: str
    label: str
    sensors: list[SensorPosition]
    note: str

