"""Fuente de datos, capacidades y control del simulador."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.acquisition.layouts import DEFAULT_MODEL, LAYOUTS, layout_for_sensors
from app.api.deps import get_container
from app.container import Container
from app.schemas.enums import DataSource, SimulatorScenario
from app.schemas.source import (
    SensorLayout,
    SimulatorConfig,
    SimulatorConfigUpdate,
    SimulatorDisconnectRequest,
    SourceSelectRequest,
    SourceStatus,
    StreamCapability,
)

router = APIRouter(prefix="/api", tags=["Fuente de datos"])
Ctx = Annotated[Container, Depends(get_container)]


@router.get("/source/status", response_model=SourceStatus, summary="Estado de la fuente de datos activa")
def source_status(ctx: Ctx) -> SourceStatus:
    return ctx.acquisition.status()


@router.get("/source/capabilities", response_model=list[StreamCapability], summary="Flujos disponibles según la fuente")
def source_capabilities(ctx: Ctx) -> list[StreamCapability]:
    return ctx.acquisition.status().streams


@router.post("/source/select", response_model=SourceStatus, summary="Selecciona la fuente de datos")
async def select_source(req: SourceSelectRequest, ctx: Ctx) -> SourceStatus:
    return await ctx.acquisition.select(req.source, force=req.force)


@router.post("/source/disconnect", response_model=SourceStatus, summary="Detiene la fuente activa")
async def disconnect_source(ctx: Ctx, force: bool = False) -> SourceStatus:
    return await ctx.acquisition.select(DataSource.DISCONNECTED, force=force)


@router.get("/layouts", response_model=list[SensorLayout], summary="Disposiciones de sensores conocidas")
def layouts() -> list[SensorLayout]:
    return list(LAYOUTS.values())


@router.get("/source/layout", response_model=SensorLayout, summary="Disposición de sensores de la fuente activa")
def source_layout(ctx: Ctx) -> SensorLayout:
    device = ctx.acquisition.status().device
    sensors = device.sensors if device else []
    for layout in LAYOUTS.values():
        if sensors and sorted(sensors) == sorted(s.id for s in layout.sensors):
            return layout
    if sensors:
        return layout_for_sensors(sensors)
    return LAYOUTS[DEFAULT_MODEL]


# --- simulador
@router.get("/simulator/config", response_model=SimulatorConfig, summary="Configuración del simulador")
def simulator_config(ctx: Ctx) -> SimulatorConfig:
    return ctx.acquisition.simulator_config


@router.get("/simulator/scenarios", summary="Escenarios disponibles (patrones ficticios)")
def simulator_scenarios() -> list[dict[str, str]]:
    descriptions = {
        SimulatorScenario.NORMAL: "Variaciones suaves y reproducibles.",
        SimulatorScenario.VARIABLE_POWER: "Mayor variación lenta de las potencias.",
        SimulatorScenario.POOR_QUALITY: "Varios sensores con calidad de contacto deficiente.",
        SimulatorScenario.TEMPORARY_DISCONNECT: "Se desconecta 6 s a los 10 s de iniciar.",
        SimulatorScenario.NO_OPTIONAL_METRICS: "No emite la métrica opcional demostrativa.",
        SimulatorScenario.ACTIVITY_DEMO: "Patrón FICTICIO por fase (referencia/matemática/respiración). No es un modelo fisiológico.",
    }
    return [{"id": s.value, "description": descriptions[s]} for s in SimulatorScenario]


@router.put("/simulator/config", response_model=SimulatorConfig, summary="Actualiza escenario, semilla o sensores deficientes")
def update_simulator(update: SimulatorConfigUpdate, ctx: Ctx) -> SimulatorConfig:
    return ctx.acquisition.update_simulator(update)


@router.post("/simulator/start", response_model=SourceStatus, summary="Activa el simulador")
async def start_simulator(ctx: Ctx, force: bool = False) -> SourceStatus:
    return await ctx.acquisition.select(DataSource.SIMULATED, force=force)


@router.post("/simulator/stop", response_model=SourceStatus, summary="Desactiva el simulador")
async def stop_simulator(ctx: Ctx, force: bool = False) -> SourceStatus:
    return await ctx.acquisition.select(DataSource.DISCONNECTED, force=force)


@router.post("/simulator/disconnect", response_model=SourceStatus, summary="Simula una desconexión del dispositivo")
async def simulator_disconnect(req: SimulatorDisconnectRequest, ctx: Ctx) -> SourceStatus:
    return await ctx.acquisition.simulate_disconnect(req.duration_s)


@router.post("/simulator/reconnect", response_model=SourceStatus, summary="Termina la desconexión simulada")
async def simulator_reconnect(ctx: Ctx) -> SourceStatus:
    return await ctx.acquisition.reconnect()

