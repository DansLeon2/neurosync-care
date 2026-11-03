"""Pruebas del adaptador EMOTIV con transportes simulados (mocks).

IMPORTANTE: estas pruebas NO validan la integración con un casco real ni con Cortex real.
Verifican el flujo de protocolo, el manejo de errores y la normalización con respuestas
cuyo formato proviene de la documentación oficial.
"""

from __future__ import annotations

import asyncio
import json
import ssl
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.acquisition.emotiv import EmotivCortexSource, build_ssl_context
from app.acquisition.emotiv_normalizer import MalformedSampleError, normalize_dev, normalize_eq, normalize_pow
from app.config import Settings
from app.schemas.enums import ConnectionState, DataSource, IntegrationState, Stream
from app.schemas.samples import SampleBatch
from app.schemas.source import SourceStatus

EPOCX = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
POW_COLS = [f"{s}/{b}" for s in EPOCX for b in ("theta", "alpha", "betaL", "betaH", "gamma")]
EQ_COLS = ["batteryPercent", "overall", "sampleRateQuality", *EPOCX]
DEV_COLS = ["Battery", "Signal", [*EPOCX, "OVERALL"], "BatteryPercent"]


def make_settings(tmp_path: Path, **kw: Any) -> Settings:
    base: dict[str, Any] = dict(
        database_url=f"sqlite:///{(tmp_path / 'x.db').as_posix()}",
        emotiv_client_id="cid",
        emotiv_client_secret="secret",
        emotiv_discovery_timeout_s=0.3,
        emotiv_retry_delay_s=0.05,
    )
    base.update(kw)
    return Settings(_env_file=None, **base)


class Sink:
    def __init__(self) -> None:
        self.batches: list[SampleBatch] = []
        self.statuses: list[SourceStatus] = []

    async def ingest(self, batch: SampleBatch) -> None:
        self.batches.append(batch)

    async def status_changed(self, status: SourceStatus) -> None:
        self.statuses.append(status)

    @property
    def states(self) -> list[IntegrationState]:
        return [s.integration_state for s in self.statuses]


class MockCortex:
    """Transporte WebSocket falso: responde a las peticiones JSON-RPC según un guion."""

    def __init__(self, handlers: dict[str, Callable[[dict[str, Any]], Any]]) -> None:
        self.handlers = handlers
        self.requests: list[dict[str, Any]] = []
        self._inbox: asyncio.Queue[str | Exception] = asyncio.Queue()
        self.closed = False

    async def send(self, message: str) -> None:
        req = json.loads(message)
        self.requests.append(req)
        handler = self.handlers.get(req["method"])
        if handler is None:
            self._inbox.put_nowait(json.dumps({"id": req["id"], "jsonrpc": "2.0", "result": {}}))
            return
        out = handler(req)
        if isinstance(out, dict) and "error" in out:
            self._inbox.put_nowait(json.dumps({"id": req["id"], "jsonrpc": "2.0", "error": out["error"]}))
        else:
            self._inbox.put_nowait(json.dumps({"id": req["id"], "jsonrpc": "2.0", "result": out}))

    async def recv(self) -> str:
        item = await self._inbox.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def close(self) -> None:
        self.closed = True

    def push(self, message: dict[str, Any]) -> None:
        self._inbox.put_nowait(json.dumps(message))

    def drop_connection(self) -> None:
        self._inbox.put_nowait(ConnectionError("socket cerrado"))

    def methods(self) -> list[str]:
        return [r["method"] for r in self.requests]


def headset(status: str = "connected", virtual: bool = False, hid: str = "EPOCX-ABC123") -> dict[str, Any]:
    return {"id": hid, "status": status, "connectedBy": "bluetooth", "firmware": "1", "isVirtual": virtual,
            "sensors": EPOCX, "settings": {"mode": "EPOC"}}


def happy_handlers(headsets: list[dict[str, Any]] | None = None, sub_failure: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    hs = headsets if headsets is not None else [headset()]
    failure = sub_failure or []

    def subscribe(req: dict[str, Any]) -> dict[str, Any]:
        cols = {"pow": POW_COLS, "eq": EQ_COLS, "dev": DEV_COLS}
        failed = {f["streamName"] for f in failure}
        return {
            "success": [{"streamName": s, "cols": cols[s], "sid": "sid-1"} for s in req["params"]["streams"] if s not in failed],
            "failure": failure,
        }

    return {
        "getCortexInfo": lambda r: {"version": "test"},
        "hasAccessRight": lambda r: {"accessGranted": True},
        "authorize": lambda r: {"cortexToken": "tok-123"},
        "controlDevice": lambda r: {"command": r["params"]["command"]},
        "queryHeadsets": lambda r: hs,
        "createSession": lambda r: {"id": "sess-1", "status": "opened"},
        "subscribe": subscribe,
        "updateSession": lambda r: {"status": "closed"},
    }


def make_source(tmp_path: Path, mock: MockCortex | None, *, source: DataSource = DataSource.REAL_EMOTIV, installed: bool | None = True,
                factory_error: Exception | None = None, **settings_kw: Any) -> tuple[EmotivCortexSource, Sink]:
    sink = Sink()

    async def factory() -> MockCortex:
        if factory_error:
            raise factory_error
        assert mock is not None
        return mock

    src = EmotivCortexSource(sink, make_settings(tmp_path, **settings_kw), source=source, transport_factory=factory,  # type: ignore[arg-type]
                             installation_probe=lambda: installed, poll_interval_s=0.02)
    return src, sink


async def wait_for(cond: Callable[[], bool], timeout: float = 2.0) -> None:
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while not cond():
        if loop.time() > end:
            raise AssertionError("condición no cumplida a tiempo")
        await asyncio.sleep(0.01)


# ------------------------------------------------------------------ normalización
def test_normalize_pow_uses_cols_not_fixed_positions() -> None:
    cols = ["O1/alpha", "AF3/theta", "AF3/betaL", "AF3/betaH", "AF3/gamma"]  # orden arbitrario
    samples = normalize_pow(cols, [3.5, 1.1, 0.2, 0.3, 0.4], 1700000000.5, DataSource.REAL_EMOTIV, "EPOCX", {"AF3": 4.0})
    by = {(s.sensor, s.metric): s for s in samples}
    assert by[("O1", "alpha")].value == 3.5
    assert by[("AF3", "low_beta")].value == 0.2 and by[("AF3", "high_beta")].value == 0.3
    assert by[("AF3", "theta")].quality == 4.0 and by[("O1", "alpha")].quality is None
    assert all(s.stream == Stream.POW and s.unit == "uV^2/Hz" and s.device_model == "EPOCX" for s in samples)
    assert samples[0].timestamp.timestamp() == pytest.approx(1700000000.5)


def test_normalize_pow_handles_missing_values_and_unknown_labels() -> None:
    samples = normalize_pow(["AF3/alpha", "AF3/delta", "weird"], [None, 1.0, 2.0], 1.0, DataSource.REAL_EMOTIV, None)
    assert len(samples) == 1  # delta no es una banda de Cortex; 'weird' se ignora
    assert samples[0].value is None and not samples[0].valid and not samples[0].active


def test_normalize_rejects_length_mismatch() -> None:
    with pytest.raises(MalformedSampleError):
        normalize_pow(["AF3/alpha", "AF3/theta"], [1.0], 1.0, DataSource.REAL_EMOTIV, None)


def test_normalize_eq_and_dev_follow_official_examples() -> None:
    insight_eq = ["batteryPercent", "overall", "sampleRateQuality", "AF3", "T7", "Pz", "T8", "AF4"]
    eq = normalize_eq(insight_eq, [78, 25, 1.0, 4, 1, 1, 2, 4], 1.0, DataSource.REAL_EMOTIV, "INSIGHT")
    m = {(s.metric, s.sensor): s.value for s in eq}
    assert m[("overall_quality", None)] == 25 and m[("sample_rate_quality", None)] == 1.0
    assert m[("sensor_quality", "T7")] == 1 and m[("battery_percent", None)] == 78

    dev = normalize_dev(["Battery", "Signal", ["AF3", "T7", "Pz", "T8", "AF4", "OVERALL"], "BatteryPercent"],
                        [3, 1, [4, 1, 1, 2, 4, 25], 74], 1.0, DataSource.REAL_EMOTIV, "INSIGHT")
    d = {(s.metric, s.sensor): s.value for s in dev}
    assert d[("contact_quality", "AF3")] == 4 and d[("overall_contact_quality", None)] == 25
    assert d[("signal", None)] == 1 and d[("battery_percent", None)] == 74 and d[("battery_level", None)] == 3
    with pytest.raises(MalformedSampleError):
        normalize_dev(DEV_COLS, [4, 2, [1, 2], 98], 1.0, DataSource.REAL_EMOTIV, None)


def test_tls_context_verifies_against_official_root_ca(tmp_path: Path) -> None:
    ctx = build_ssl_context(make_settings(tmp_path).emotiv_ca_file)
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname  # nunca se desactiva la verificación
    assert ctx.cert_store_stats()["x509_ca"] >= 1


def test_streams_are_restricted_to_authorized_set(tmp_path: Path) -> None:
    s = make_settings(tmp_path, emotiv_streams=["pow", "eeg", "met", "eq"])
    assert s.emotiv_streams == ["pow", "eq"]  # 'eeg' (licencia de pago) y 'met' quedan fuera


# ------------------------------------------------------------------ estados de integración
def test_credentials_missing(tmp_path: Path) -> None:
    async def run() -> None:
        src, sink = make_source(tmp_path, None, emotiv_client_id="", emotiv_client_secret="")
        await src.start()
        await wait_for(lambda: IntegrationState.CREDENTIALS_MISSING in sink.states)
        assert "EMOTIV_CLIENT_ID" in src.status().message
        await src.stop()

    asyncio.run(run())


def test_cortex_unavailable_and_not_installed(tmp_path: Path) -> None:
    async def run() -> None:
        src, sink = make_source(tmp_path, None, installed=True, factory_error=ConnectionRefusedError())
        await src.start()
        await wait_for(lambda: IntegrationState.CORTEX_UNAVAILABLE in sink.states)
        await src.stop()
        src2, sink2 = make_source(tmp_path, None, installed=False, factory_error=ConnectionRefusedError())
        await src2.start()
        await wait_for(lambda: IntegrationState.CORTEX_NOT_INSTALLED in sink2.states)
        await src2.stop()

    asyncio.run(run())


def test_tls_failure_is_reported_and_not_retried_insecurely(tmp_path: Path) -> None:
    async def run() -> None:
        src, sink = make_source(tmp_path, None, factory_error=ssl.SSLCertVerificationError("bad cert"))
        await src.start()
        await wait_for(lambda: IntegrationState.COMMUNICATION_ERROR in sink.states)
        assert "TLS" in src.status().message
        await src.stop()

    asyncio.run(run())


def test_authorization_pending_then_granted(tmp_path: Path) -> None:
    async def run() -> None:
        calls = {"n": 0}

        def has_access(req: dict[str, Any]) -> dict[str, Any]:
            calls["n"] += 1
            return {"accessGranted": calls["n"] > 3}

        h = happy_handlers()
        h["hasAccessRight"] = has_access
        h["requestAccess"] = lambda r: {"accessGranted": False, "message": "Aprueba en Launcher"}
        mock = MockCortex(h)
        src, sink = make_source(tmp_path, mock)
        await src.start()
        await wait_for(lambda: IntegrationState.AUTHORIZATION_PENDING in sink.states)
        await wait_for(lambda: "subscribe" in mock.methods())
        assert mock.methods().index("requestAccess") < mock.methods().index("authorize")
        await src.stop()

    asyncio.run(run())


def test_invalid_credentials(tmp_path: Path) -> None:
    async def run() -> None:
        h = happy_handlers()
        h["authorize"] = lambda r: {"error": {"code": -32021, "message": "Invalid client credentials"}}
        src, sink = make_source(tmp_path, MockCortex(h))
        await src.start()
        await wait_for(lambda: IntegrationState.CREDENTIALS_INVALID in sink.states)
        await src.stop()

    asyncio.run(run())


def test_device_not_found(tmp_path: Path) -> None:
    async def run() -> None:
        src, sink = make_source(tmp_path, MockCortex(happy_handlers(headsets=[])))
        await src.start()
        await wait_for(lambda: IntegrationState.DEVICE_NOT_FOUND in sink.states)
        assert "casco" in src.status().message
        await src.stop()

    asyncio.run(run())


def test_virtual_and_real_sources_pick_the_matching_headsets_only(tmp_path: Path) -> None:
    async def run() -> None:
        hs = [headset(virtual=True, hid="EPOCX-VIRTUAL"), headset(virtual=False, hid="EPOCX-REAL")]
        mock_real = MockCortex(happy_handlers(headsets=hs))
        real, _ = make_source(tmp_path, mock_real, source=DataSource.REAL_EMOTIV)
        await real.start()
        await wait_for(lambda: "createSession" in mock_real.methods())
        create = next(r for r in mock_real.requests if r["method"] == "createSession")
        assert create["params"]["headset"] == "EPOCX-REAL" and create["params"]["status"] == "open"
        await real.stop()

        mock_virtual = MockCortex(happy_handlers(headsets=hs))
        virtual, _ = make_source(tmp_path, mock_virtual, source=DataSource.VIRTUAL_DEVICE)
        await virtual.start()
        await wait_for(lambda: "createSession" in mock_virtual.methods())
        assert next(r for r in mock_virtual.requests if r["method"] == "createSession")["params"]["headset"] == "EPOCX-VIRTUAL"
        assert virtual.status().device.is_virtual is True  # type: ignore[union-attr]
        await virtual.stop()

        only_real = MockCortex(happy_handlers(headsets=[headset(virtual=False)]))
        v2, sink = make_source(tmp_path, only_real, source=DataSource.VIRTUAL_DEVICE)
        await v2.start()
        await wait_for(lambda: IntegrationState.DEVICE_NOT_FOUND in sink.states)
        assert "virtual" in v2.status().message.lower()
        await v2.stop()

    asyncio.run(run())


def test_discovered_headset_is_connected_before_creating_session(tmp_path: Path) -> None:
    async def run() -> None:
        state = {"status": "discovered"}

        def query(req: dict[str, Any]) -> list[dict[str, Any]]:
            return [headset(status=state["status"])]

        def control(req: dict[str, Any]) -> dict[str, Any]:
            if req["params"]["command"] == "connect":
                state["status"] = "connected"
            return {}

        h = happy_handlers()
        h["queryHeadsets"], h["controlDevice"] = query, control
        mock = MockCortex(h)
        src, _ = make_source(tmp_path, mock)
        await src.start()
        await wait_for(lambda: "createSession" in mock.methods())
        connects = [r for r in mock.requests if r["method"] == "controlDevice" and r["params"]["command"] == "connect"]
        assert len(connects) == 1
        await src.stop()

    asyncio.run(run())


def test_streaming_pipeline_end_to_end_with_mock_samples(tmp_path: Path) -> None:
    async def run() -> None:
        mock = MockCortex(happy_handlers())
        src, sink = make_source(tmp_path, mock)
        await src.start()
        await wait_for(lambda: "subscribe" in mock.methods())
        sub = next(r for r in mock.requests if r["method"] == "subscribe")
        assert sub["params"]["streams"] == ["dev", "eq", "pow"] and sub["params"]["cortexToken"] == "tok-123"
        assert "met" not in sub["params"]["streams"] and "eeg" not in sub["params"]["streams"]

        mock.push({"eq": [90, 80, 1.0, *([4] * 14)], "sid": "sid-1", "time": 1700000000.0})
        pow_values = [float(i) for i in range(len(POW_COLS))]
        mock.push({"pow": pow_values, "sid": "sid-1", "time": 1700000000.125})
        await wait_for(lambda: any(b.samples[0].stream == Stream.POW for b in sink.batches))

        pow_batch = next(b for b in sink.batches if b.samples[0].stream == Stream.POW)
        assert len(pow_batch.samples) == 70 and pow_batch.source == DataSource.REAL_EMOTIV
        first = pow_batch.samples[0]
        assert (first.sensor, first.metric, first.value, first.quality) == ("AF3", "theta", 0.0, 4.0)
        assert pow_batch.device_model == "EPOCX"
        await wait_for(lambda: src.status().integration_state == IntegrationState.CONNECTED_STREAMING)
        st = src.status()
        assert st.connection == ConnectionState.STREAMING and st.simulated is False and st.device.is_virtual is False  # type: ignore[union-attr]
        await src.stop()
        assert mock.closed
        assert any(r["method"] == "updateSession" and r["params"]["status"] == "close" for r in mock.requests)
        assert src.status().connection == ConnectionState.DISCONNECTED

    asyncio.run(run())


def test_malformed_stream_message_is_dropped_without_crashing(tmp_path: Path) -> None:
    async def run() -> None:
        mock = MockCortex(happy_handlers())
        src, sink = make_source(tmp_path, mock)
        await src.start()
        await wait_for(lambda: "subscribe" in mock.methods())
        mock.push({"pow": [1.0, 2.0], "sid": "sid-1", "time": 1.0})  # longitud incoherente con cols
        mock.push({"pow": [1.0] * len(POW_COLS), "sid": "sid-1", "time": 2.0})
        await wait_for(lambda: len(sink.batches) == 1)
        await src.stop()

    asyncio.run(run())


def test_pow_stream_not_authorized(tmp_path: Path) -> None:
    async def run() -> None:
        failure = [{"streamName": "pow", "code": -32016, "message": "Invalid stream"}]
        src, sink = make_source(tmp_path, MockCortex(happy_handlers(sub_failure=failure)))
        await src.start()
        await wait_for(lambda: IntegrationState.STREAM_NOT_AUTHORIZED in sink.states)
        caps = {c.stream: c.state for c in src.status().streams}
        assert caps["pow"] == "not_authorized" and caps["eq"] == "available"
        await src.stop()

    asyncio.run(run())


def test_headset_disconnect_warning_triggers_reconnect_flow(tmp_path: Path) -> None:
    async def run() -> None:
        mock = MockCortex(happy_handlers())
        src, sink = make_source(tmp_path, mock)
        await src.start()
        await wait_for(lambda: "subscribe" in mock.methods())
        mock.push({"warning": {"code": 103, "message": {}}})
        await wait_for(lambda: IntegrationState.DEVICE_DISCONNECTED in sink.states)
        assert sink.statuses[-1].connection in (ConnectionState.SIGNAL_LOST, ConnectionState.CONNECTING)
        await src.stop()

    asyncio.run(run())


def test_socket_drop_is_reported_as_communication_error(tmp_path: Path) -> None:
    async def run() -> None:
        mock = MockCortex(happy_handlers())
        src, sink = make_source(tmp_path, mock, emotiv_retry_delay_s=5.0)
        await src.start()
        await wait_for(lambda: "subscribe" in mock.methods())
        mock.drop_connection()
        await wait_for(lambda: IntegrationState.COMMUNICATION_ERROR in sink.states)
        await src.stop()

    asyncio.run(run())


def test_secret_is_never_exposed_in_status_or_repr(tmp_path: Path) -> None:
    secret_val = "super-confidential-token-98765"
    settings = make_settings(tmp_path, emotiv_client_secret=secret_val)
    assert secret_val not in repr(settings)
    src, _ = make_source(tmp_path, None, emotiv_client_secret=secret_val)
    assert secret_val not in src.status().model_dump_json()

