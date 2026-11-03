"""Pruebas del simulador y del contrato de muestras."""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime, timedelta

from app.acquisition.simulator import SimulatedSource
from app.schemas.enums import BANDS, DataSource, PhaseKind, SimulatorScenario, Stream
from app.schemas.samples import UNIT_POW_SIMULATED, Sample, SampleBatch
from app.schemas.source import SimulatorConfig, SourceStatus

T0 = datetime(2026, 11, 3, 18, 0, 0, tzinfo=UTC)


class FakeSink:
    def __init__(self) -> None:
        self.batches: list[SampleBatch] = []
        self.statuses: list[SourceStatus] = []

    async def ingest(self, batch: SampleBatch) -> None:
        self.batches.append(batch)

    async def status_changed(self, status: SourceStatus) -> None:
        self.statuses.append(status)


def make_sim(**cfg) -> SimulatedSource:  # type: ignore[no-untyped-def]
    return SimulatedSource(FakeSink(), SimulatorConfig(**cfg))


def values_of(batch: SampleBatch) -> list[float | None]:
    return [s.value for s in batch.samples if s.stream == Stream.POW]


def test_tick_contains_all_sensors_and_bands() -> None:
    sim = make_sim(seed=1)
    batch = sim.generate_tick(T0)
    assert batch is not None
    pow_samples = [s for s in batch.samples if s.stream == Stream.POW]
    assert len(pow_samples) == 14 * len(BANDS)
    assert {s.metric for s in pow_samples} == set(BANDS)
    assert all(s.source == DataSource.SIMULATED for s in batch.samples)
    assert all(s.unit == UNIT_POW_SIMULATED for s in pow_samples)  # unidades arbitrarias, no uV^2/Hz reales
    assert all(s.valid and s.value is not None and s.value > 0 for s in pow_samples)
    assert all(s.timestamp.tzinfo is not None for s in batch.samples)


def test_same_seed_is_reproducible_and_different_seed_differs() -> None:
    a, b, c = make_sim(seed=5), make_sim(seed=5), make_sim(seed=6)
    seq_a = [values_of(a.generate_tick(T0 + timedelta(seconds=i))) for i in range(20)]  # type: ignore[arg-type]
    seq_b = [values_of(b.generate_tick(T0 + timedelta(seconds=i))) for i in range(20)]  # type: ignore[arg-type]
    seq_c = [values_of(c.generate_tick(T0 + timedelta(seconds=i))) for i in range(20)]  # type: ignore[arg-type]
    assert seq_a == seq_b
    assert seq_a != seq_c


def test_values_vary_smoothly_over_time() -> None:
    sim = make_sim(seed=2)
    series = []
    for i in range(40):
        batch = sim.generate_tick(T0 + timedelta(milliseconds=125 * i))
        assert batch is not None
        series.append(next(s.value for s in batch.samples if s.stream == Stream.POW and s.sensor == "O1" and s.metric == "alpha"))
    assert len({round(v, 4) for v in series}) > 10  # no es constante
    steps = [abs(math.log(series[i + 1] / series[i])) for i in range(len(series) - 1)]
    assert max(steps) < 0.5  # cambios suaves entre muestras consecutivas


def test_eq_and_dev_streams_are_emitted_at_their_own_rate() -> None:
    sim = make_sim()
    streams_by_tick = [{s.stream for s in sim.generate_tick(T0).samples} for _ in range(8)]  # type: ignore[union-attr]
    assert Stream.EQ in streams_by_tick[0] and Stream.EQ not in streams_by_tick[1]
    assert Stream.DEV in streams_by_tick[0]


def test_poor_quality_scenario_lowers_sensor_quality() -> None:
    sim = make_sim(scenario=SimulatorScenario.POOR_QUALITY)
    batch = sim.generate_tick(T0)
    assert batch is not None
    q = {s.sensor: s.value for s in batch.samples if s.metric == "sensor_quality"}
    overall = next(s.value for s in batch.samples if s.metric == "overall_quality")
    assert min(q.values()) <= 2 and max(q.values()) == 4
    assert overall is not None and overall < 100


def test_configurable_poor_sensors() -> None:
    sim = make_sim(poor_sensors=["AF3", "O2"])
    batch = sim.generate_tick(T0)
    assert batch is not None
    q = {s.sensor: s.value for s in batch.samples if s.metric == "sensor_quality"}
    assert q["AF3"] == 1 and q["O2"] == 1 and q["F3"] == 4


def test_disconnect_emits_no_samples_and_reconnect_resumes() -> None:
    sim = make_sim()
    assert sim.generate_tick(T0) is not None
    sim.simulate_disconnect(None, now=T0)
    assert sim.disconnected
    assert sim.generate_tick(T0 + timedelta(seconds=1)) is None  # no se inventan muestras
    sim.reconnect()
    assert sim.generate_tick(T0 + timedelta(seconds=2)) is not None


def test_timed_disconnect_expires_on_schedule() -> None:
    sim = make_sim()
    sim.simulate_disconnect(2.0, now=T0)
    assert not sim._update_disconnect_schedule(T0 + timedelta(seconds=1))
    assert sim._update_disconnect_schedule(T0 + timedelta(seconds=3))
    assert not sim.disconnected


def test_optional_metrics_absent_in_dedicated_scenario() -> None:
    with_met = make_sim(scenario=SimulatorScenario.NORMAL)
    without = make_sim(scenario=SimulatorScenario.NO_OPTIONAL_METRICS)
    assert any(s.stream == Stream.MET for s in with_met.generate_tick(T0).samples)  # type: ignore[union-attr]
    assert not any(s.stream == Stream.MET for s in without.generate_tick(T0).samples)  # type: ignore[union-attr]
    assert not without.emits_optional_metrics()
    cap = {c.stream: c for c in without.capabilities()}
    assert cap["met"].state == "unavailable" and cap["eeg"].state == "disabled"


def test_activity_demo_pattern_is_fictitious_and_only_in_that_scenario() -> None:
    def mean_band(scenario: SimulatorScenario, phase: PhaseKind | None, band: str) -> float:
        sim = make_sim(seed=3, scenario=scenario)
        sim.set_phase_context(phase)
        vals = []
        for i in range(200):
            batch = sim.generate_tick(T0 + timedelta(milliseconds=125 * i))
            assert batch is not None
            vals += [s.value for s in batch.samples if s.stream == Stream.POW and s.metric == band and s.value]
        return sum(vals) / len(vals)

    base = mean_band(SimulatorScenario.ACTIVITY_DEMO, None, "alpha")
    calm = mean_band(SimulatorScenario.ACTIVITY_DEMO, PhaseKind.REGULATION, "alpha")
    assert calm > base * 1.1
    normal_a = mean_band(SimulatorScenario.NORMAL, None, "alpha")
    normal_b = mean_band(SimulatorScenario.NORMAL, PhaseKind.REGULATION, "alpha")
    assert normal_a == normal_b  # sin patrón fuera de ACTIVITY_DEMO


def test_status_always_flags_simulated_data() -> None:
    sim = make_sim()
    st = sim.status()
    assert st.simulated and st.source == DataSource.SIMULATED
    assert st.device is not None and st.device.id is None  # no hay dispositivo conectado
    assert "SIMULADO" in sim.status().message or sim.status().connection.value == "DISCONNECTED"


def test_sample_validation_marks_missing_and_non_finite() -> None:
    kw = dict(timestamp=T0, source=DataSource.SIMULATED, stream=Stream.POW, metric="alpha", unit="u")
    ok = Sample(value=1.5, **kw)  # type: ignore[arg-type]
    assert ok.valid and ok.active
    for bad in (None, float("nan"), float("inf")):
        s = Sample(value=bad, **kw)  # type: ignore[arg-type]
        assert s.value is None and not s.valid and not s.active
    naive = Sample(value=1.0, **{**kw, "timestamp": datetime(2026, 1, 1)})  # type: ignore[arg-type]
    assert naive.timestamp.tzinfo is not None


def test_async_run_streams_batches_and_stops() -> None:
    async def scenario() -> None:
        sink = FakeSink()
        sim = SimulatedSource(sink, SimulatorConfig(seed=1), pow_hz=100.0)
        await sim.start()
        await asyncio.sleep(0.3)
        await sim.stop()
        n = len(sink.batches)
        assert n >= 10
        await asyncio.sleep(0.1)
        assert len(sink.batches) == n  # detenido
        assert sim.status().connection.value == "DISCONNECTED"

    asyncio.run(scenario())

