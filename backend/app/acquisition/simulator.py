"""Simulador de adquisición EEG (DATOS SIMULADOS).

IMPORTANTE
----------
* Todo lo que genera este módulo es **sintético**. No son mediciones de ninguna
  persona ni de ningún dispositivo. Cada muestra lleva ``source=SIMULATED`` y unidades
  arbitrarias (``u.a. (simulado)``), no µV²/Hz reales.
* Los patrones asociados a actividades (escenario ``ACTIVITY_DEMO``) son **ficticios**,
  solo sirven para demostrar el software y comparar fases en los reportes. No son
  modelos fisiológicos validados.
* Las tasas (pow 8 Hz, eq 2 Hz, dev 2 Hz) replican las documentadas por EMOTIV para
  que el pipeline se ejercite igual que con Cortex.

Genera muestras con la misma forma que producirá ``EmotivCortexSource``.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
from datetime import datetime, timedelta

import numpy as np

from app.acquisition.base import DataSourceAdapter, SampleSink
from app.acquisition.layouts import DEFAULT_MODEL, LAYOUTS
from app.schemas.enums import (
    BANDS,
    ConnectionState,
    DataSource,
    IntegrationState,
    PhaseKind,
    SimulatorScenario,
    Stream,
)
from app.schemas.samples import (
    UNIT_DEMO,
    UNIT_PERCENT,
    UNIT_POW_SIMULATED,
    UNIT_QUALITY_OVERALL,
    UNIT_QUALITY_SENSOR,
    UNIT_SIGNAL,
    UNIT_SRQ,
    Sample,
    SampleBatch,
    utcnow,
)
from app.schemas.source import DeviceInfo, SimulatorConfig, SourceStatus, StreamCapability

# Valores base arbitrarios por banda (unidades arbitrarias, no físicas).
_BAND_BASE = {"theta": 1.0, "alpha": 1.4, "low_beta": 0.7, "high_beta": 0.5, "gamma": 0.3}
_BAND_PERIOD_S = {"theta": 23.0, "alpha": 17.0, "low_beta": 29.0, "high_beta": 37.0, "gamma": 43.0}

_POSTERIOR = {"O1", "O2", "P7", "P8", "Pz"}
_FRONTAL = {"AF3", "AF4", "F3", "F4", "F7", "F8"}

POW_HZ = 8.0
EQ_HZ = 2.0
DEV_HZ = 2.0
MET_HZ = 0.5

# Modulación ficticia por fase (solo ACTIVITY_DEMO). Multiplicadores en escala log.
_PHASE_PATTERN: dict[PhaseKind, dict[str, float]] = {
    PhaseKind.BASELINE: {},
    PhaseKind.MATH: {"low_beta": 0.30, "high_beta": 0.35, "alpha": -0.18},
    PhaseKind.REGULATION: {"alpha": 0.30, "theta": 0.12, "high_beta": -0.20},
}


def _sensor_weight(sensor: str, band: str) -> float:
    """Pequeñas diferencias topográficas ficticias para que el mapa no sea uniforme."""
    w = 1.0
    if band == "alpha" and sensor in _POSTERIOR:
        w = 1.45
    elif band in ("low_beta", "high_beta") and sensor in _FRONTAL:
        w = 1.25
    elif band == "theta" and sensor in _FRONTAL:
        w = 1.15
    elif band == "gamma" and sensor.startswith("T"):
        w = 1.2
    return w


class SimulatedSource(DataSourceAdapter):
    source = DataSource.SIMULATED

    def __init__(
        self,
        sink: SampleSink,
        config: SimulatorConfig | None = None,
        *,
        model: str = DEFAULT_MODEL,
        pow_hz: float = POW_HZ,
    ) -> None:
        super().__init__(sink)
        self.config = config or SimulatorConfig()
        self.model = model
        self.sensors = [s.id for s in LAYOUTS[model].sensors]
        self.pow_hz = pow_hz
        self._eq_every = max(1, round(pow_hz / EQ_HZ))
        self._dev_every = max(1, round(pow_hz / DEV_HZ))
        self._met_every = max(1, round(pow_hz / MET_HZ))
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._manual_disconnect = False
        self._disconnect_until: datetime | None = None
        self._phase_context: PhaseKind | None = None
        self._last_sample_at: datetime | None = None
        self._auto_disconnect_done = False
        self._started_at: datetime | None = None
        self._reset_state()

    # ------------------------------------------------------------------ estado
    def _reset_state(self) -> None:
        self._rng = np.random.default_rng(self.config.seed)
        self._tick = 0
        n = (len(self.sensors), len(BANDS))
        self._ou = np.zeros(n)
        self._phases = self._rng.uniform(0, 2 * math.pi, size=len(BANDS))
        self._sensor_offset = self._rng.normal(0.0, 0.08, size=n)
        self._battery = 92.0

    @property
    def disconnected(self) -> bool:
        return self._manual_disconnect

    def emits_optional_metrics(self) -> bool:
        return self.config.scenario != SimulatorScenario.NO_OPTIONAL_METRICS

    # --------------------------------------------------------------- controles
    def set_config(self, config: SimulatorConfig) -> None:
        reseed = config.seed != self.config.seed
        self.config = config
        if reseed:
            self._reset_state()
        self._auto_disconnect_done = False
        self._started_at = utcnow()

    def set_phase_context(self, kind: PhaseKind | None) -> None:
        self._phase_context = kind

    def simulate_disconnect(self, duration_s: float | None = 5.0, now: datetime | None = None) -> None:
        self._manual_disconnect = True
        now = now or utcnow()
        self._disconnect_until = now + timedelta(seconds=duration_s) if duration_s else None

    def reconnect(self) -> None:
        self._manual_disconnect = False
        self._disconnect_until = None

    # --------------------------------------------------------------- generación
    def _sensor_quality(self) -> dict[str, float]:
        """Calidad por sensor (0-4) según el escenario y sensores deficientes."""
        poor = set(self.config.poor_sensors)
        scenario = self.config.scenario
        q: dict[str, float] = {}
        for i, s in enumerate(self.sensors):
            val = 4.0
            if scenario == SimulatorScenario.POOR_QUALITY and i % 3 == 0:
                val = 1.0 if i % 2 == 0 else 2.0
            if s in poor:
                val = 1.0
            q[s] = val
        return q

    def generate_tick(self, ts: datetime) -> SampleBatch | None:
        """Genera el lote de muestras de un instante. Determinista dado el seed y la secuencia.

        Devuelve ``None`` si la fuente está en desconexión simulada (no se inventan muestras).
        """
        if self._manual_disconnect:
            return None
        scenario = self.config.scenario
        quality = self._sensor_quality()
        t = self._tick / self.pow_hz
        amp = 0.55 if scenario == SimulatorScenario.VARIABLE_POWER else 0.18
        pattern = _PHASE_PATTERN.get(self._phase_context, {}) if scenario == SimulatorScenario.ACTIVITY_DEMO and self._phase_context else {}

        noise = self._rng.normal(0.0, 1.0, size=self._ou.shape)
        self._ou = 0.92 * self._ou + 0.05 * noise
        noisy_sensor = np.array([2.2 if quality[s] <= 2 else 1.0 for s in self.sensors])[:, None]

        samples: list[Sample] = []
        common = {"timestamp": ts, "source": DataSource.SIMULATED, "device_model": None}
        for si, sensor in enumerate(self.sensors):
            q = quality[sensor]
            for bi, band in enumerate(BANDS):
                slow = amp * math.sin(2 * math.pi * t / _BAND_PERIOD_S[band] + self._phases[bi])
                logv = slow + self._ou[si, bi] * noisy_sensor[si, 0] + self._sensor_offset[si, bi] + pattern.get(band, 0.0)
                value = _BAND_BASE[band] * _sensor_weight(sensor, band) * math.exp(logv)
                samples.append(
                    Sample(
                        **common,
                        stream=Stream.POW,
                        sensor=sensor,
                        metric=band,
                        value=None if q <= 0 else round(float(value), 5),
                        unit=UNIT_POW_SIMULATED,
                        quality=q,
                        raw_label=f"{sensor}/{band}",
                    )
                )

        if self._tick % self._eq_every == 0:
            srq = 1.0 if scenario != SimulatorScenario.POOR_QUALITY else 0.92
            for sensor in self.sensors:
                samples.append(
                    Sample(**common, stream=Stream.EQ, sensor=sensor, metric="sensor_quality", value=quality[sensor], unit=UNIT_QUALITY_SENSOR)
                )
            overall = float(np.mean(list(quality.values()))) / 4.0 * 100.0
            samples.append(Sample(**common, stream=Stream.EQ, metric="overall_quality", value=round(overall, 1), unit=UNIT_QUALITY_OVERALL))
            samples.append(Sample(**common, stream=Stream.EQ, metric="sample_rate_quality", value=srq, unit=UNIT_SRQ))

        if self._tick % self._dev_every == 0:
            self._battery = max(5.0, self._battery - 0.0005)
            samples.append(Sample(**common, stream=Stream.DEV, metric="battery_percent", value=round(self._battery, 1), unit=UNIT_PERCENT))
            samples.append(Sample(**common, stream=Stream.DEV, metric="signal", value=1.0, unit=UNIT_SIGNAL))
            for sensor in self.sensors:
                samples.append(
                    Sample(**common, stream=Stream.DEV, sensor=sensor, metric="contact_quality", value=quality[sensor], unit=UNIT_QUALITY_SENSOR)
                )

        if self.emits_optional_metrics() and self._tick % self._met_every == 0:
            demo = 0.5 + 0.35 * math.sin(2 * math.pi * t / 41.0 + float(self._phases[0]))
            samples.append(Sample(**common, stream=Stream.MET, metric="demo_index", value=round(demo, 4), unit=UNIT_DEMO))

        self._tick += 1
        return SampleBatch(timestamp=ts, source=DataSource.SIMULATED, samples=samples)

    # ------------------------------------------------------------------ ciclo
    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._started_at = utcnow()
        self._auto_disconnect_done = False
        self._task = asyncio.create_task(self._run(), name="simulator")
        await self._sink.status_changed(self.status())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def _update_disconnect_schedule(self, now: datetime) -> bool:
        """Devuelve True si el estado de desconexión cambió."""
        changed = False
        if self._manual_disconnect and self._disconnect_until and now >= self._disconnect_until:
            self.reconnect()
            changed = True
        # Escenario de desconexión temporal: una sola vez, 10 s después de iniciar, durante 6 s.
        if (
            self.config.scenario == SimulatorScenario.TEMPORARY_DISCONNECT
            and not self._auto_disconnect_done
            and self._started_at
            and (now - self._started_at).total_seconds() >= 10
        ):
            self._auto_disconnect_done = True
            self.simulate_disconnect(6.0, now)
            changed = True
        return changed

    async def _run(self) -> None:
        interval = 1.0 / self.pow_hz
        loop = asyncio.get_running_loop()
        next_t = loop.time()
        was_disconnected = False
        while self._running:
            now = utcnow()
            if self._update_disconnect_schedule(now) or self._manual_disconnect != was_disconnected:
                was_disconnected = self._manual_disconnect
                await self._sink.status_changed(self.status())
            batch = self.generate_tick(now)
            if batch is not None:
                self._last_sample_at = now
                await self._sink.ingest(batch)
            next_t += interval
            await asyncio.sleep(max(0.0, next_t - loop.time()))

    # ------------------------------------------------------------------ estado
    def capabilities(self) -> list[StreamCapability]:
        met_state = "available" if self.emits_optional_metrics() else "unavailable"
        return [
            StreamCapability(stream="pow", label="Potencia de bandas", state="available", rate_hz=self.pow_hz, note="Simulado"),
            StreamCapability(stream="eq", label="Calidad EEG", state="available", rate_hz=EQ_HZ, note="Simulado"),
            StreamCapability(stream="dev", label="Dispositivo y contacto", state="available", rate_hz=DEV_HZ, note="Simulado"),
            StreamCapability(
                stream="met",
                label="Métrica demostrativa",
                state=met_state,
                rate_hz=MET_HZ if met_state == "available" else None,
                note="Valor ficticio de demostración (no es una métrica real de EMOTIV)"
                if met_state == "available"
                else "Escenario sin métricas opcionales",
            ),
            StreamCapability(stream="eeg", label="EEG sin procesar", state="disabled", note="No se simula ni se usa en el MVP"),
        ]

    def status(self) -> SourceStatus:
        if not self._running:
            connection = ConnectionState.DISCONNECTED
            message = "Simulador detenido."
        elif self._manual_disconnect:
            connection = ConnectionState.SIGNAL_LOST
            message = "Desconexión simulada: no se generan muestras."
        else:
            connection = ConnectionState.STREAMING
            message = "DATOS SIMULADOS: no hay ningún dispositivo conectado."
        return SourceStatus(
            source=DataSource.SIMULATED,
            simulated=True,
            connection=connection,
            integration_state=IntegrationState.NOT_APPLICABLE,
            message=message,
            device=DeviceInfo(id=None, model=None, is_virtual=None, sensors=list(self.sensors), battery_percent=round(self._battery, 1)),
            scenario=self.config.scenario,
            last_sample_at=self._last_sample_at,
            streams=self.capabilities(),
        )

