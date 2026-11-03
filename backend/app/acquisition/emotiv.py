"""Adaptador ``EmotivCortexSource`` para la API Cortex de EMOTIV (JSON-RPC sobre WebSocket seguro).

ORIGEN DEL CÓDIGO (ver docs/EMOTIV_INTEGRATION.md)
--------------------------------------------------
* Del ejemplo oficial https://github.com/Emotiv/cortex-example (licencia MIT, © 2020 EMOTIV),
  archivo ``python/cortex.py``, solo se reutilizan los **patrones de protocolo**: orden de
  llamadas (hasAccessRight → requestAccess → authorize → queryHeadsets → controlDevice →
  createSession → subscribe), códigos de advertencia y la verificación TLS contra el
  certificado ``rootCA.pem`` oficial (incluido en ``certs/``).
* La implementación (asyncio, máquina de estados, normalización, reconexión, pruebas con
  mocks) es **propia**.

ESTADO DE VALIDACIÓN
--------------------
Probado únicamente con transportes simulados (mocks). NO se ha validado con un casco real
ni con Virtual Brainwear; ver docs/TESTING.md.

No se usan los flujos ``eeg`` (licencia de pago) ni ``met`` (métricas restringidas).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import ssl
import sys
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.acquisition.base import DataSourceAdapter, SampleSink
from app.acquisition.emotiv_normalizer import MalformedSampleError, normalize_dev, normalize_eq, normalize_pow
from app.config import Settings
from app.schemas.enums import ConnectionState, DataSource, IntegrationState
from app.schemas.samples import SampleBatch, utcnow
from app.schemas.source import DeviceInfo, SourceStatus, StreamCapability

log = logging.getLogger(__name__)

# Códigos de advertencia de Cortex (ejemplo oficial cortex.py / documentación).
WARN_CORTEX_STOP_ALL_STREAMS = 0
WARN_CORTEX_CLOSE_SESSION = 1
WARN_ACCESS_RIGHT_GRANTED = 9
WARN_ACCESS_RIGHT_REJECTED = 10
WARN_HEADSET_DISCONNECTED_TIMEOUT = 103
WARN_HEADSET_CONNECTED = 104
WARN_HEADSET_CANNOT_CONNECT_TIMEOUT = 102

# Códigos de error de Cortex (documentación "Error Codes").
ERR_HEADSET_UNAVAILABLE = -32004
ERR_INVALID_CLIENT_CREDENTIALS = -32021
ERR_NOT_APPROVED_IN_LAUNCHER = -32102

STREAM_LABELS = {"pow": "Potencia de bandas", "eq": "Calidad EEG", "dev": "Dispositivo y contacto"}
STREAM_RATES = {"pow": 8.0, "eq": 2.0, "dev": 2.0}  # documentados por EMOTIV
STALE_AFTER_S = 5.0


class CortexError(Exception):
    def __init__(self, code: int | None, message: str) -> None:
        super().__init__(f"Cortex error {code}: {message}")
        self.code = code
        self.message = message


class CortexTransport(Protocol):
    async def send(self, message: str) -> None: ...
    async def recv(self) -> str: ...
    async def close(self) -> None: ...


TransportFactory = Callable[[], Awaitable[CortexTransport]]


def build_ssl_context(ca_file: Path) -> ssl.SSLContext:
    """Contexto TLS con verificación obligatoria contra la CA oficial de EMOTIV."""
    return ssl.create_default_context(cafile=str(ca_file))


def websocket_transport_factory(url: str, ca_file: Path) -> TransportFactory:
    async def factory() -> CortexTransport:
        from websockets.asyncio.client import connect

        return await connect(url, ssl=build_ssl_context(ca_file), open_timeout=5, ping_interval=None)  # type: ignore[return-value]

    return factory


def detect_cortex_installation() -> bool | None:
    """Heurística: busca "EMOTIV" entre los programas instalados (solo Windows).

    Devuelve ``None`` si no se puede determinar (otros sistemas operativos).
    """
    if sys.platform != "win32":
        return None
    import winreg

    paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, path in paths:
        try:
            with winreg.OpenKey(hive, path) as key:
                count = winreg.QueryInfoKey(key)[0]
                for i in range(count):
                    try:
                        with winreg.OpenKey(key, winreg.EnumKey(key, i)) as sub:
                            name = str(winreg.QueryValueEx(sub, "DisplayName")[0])
                    except OSError:
                        continue
                    if "emotiv" in name.lower():
                        return True
        except OSError:
            continue
    return False


class CortexRpc:
    """Cliente JSON-RPC mínimo: correlaciona respuestas por ``id`` y reenvía flujos y advertencias."""

    def __init__(
        self,
        transport: CortexTransport,
        on_stream: Callable[[dict[str, Any]], None],
        on_warning: Callable[[dict[str, Any]], None],
    ) -> None:
        self._transport = transport
        self._on_stream = on_stream
        self._on_warning = on_warning
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._next_id = 1
        self._reader: asyncio.Task[None] | None = None
        self.closed = asyncio.Event()
        self.close_reason: BaseException | None = None

    def start(self) -> None:
        self._reader = asyncio.create_task(self._read_loop(), name="cortex-reader")

    async def _read_loop(self) -> None:
        import json

        try:
            while True:
                raw = await self._transport.recv()
                try:
                    msg = json.loads(raw)
                except ValueError:
                    log.warning("Mensaje no JSON recibido de Cortex")
                    continue
                self._dispatch(msg)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # cierre del socket o error de transporte
            self.close_reason = exc
        finally:
            self.closed.set()
            err = ConnectionError("Conexión con Cortex cerrada")
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(err)
            self._pending.clear()

    def _dispatch(self, msg: dict[str, Any]) -> None:
        if not isinstance(msg, dict):
            return
        try:
            if "id" in msg and ("result" in msg or "error" in msg):
                fut = self._pending.pop(msg["id"], None)
                if fut and not fut.done():
                    if "error" in msg:
                        err = msg["error"] or {}
                        fut.set_exception(CortexError(err.get("code"), str(err.get("message", ""))))
                    else:
                        fut.set_result(msg["result"])
            elif "sid" in msg:
                self._on_stream(msg)
            elif "warning" in msg:
                self._on_warning(msg["warning"])
        except Exception:  # un callback defectuoso no debe matar el lector
            log.exception("Error procesando mensaje de Cortex")

    async def call(self, method: str, params: dict[str, Any] | None = None, timeout: float = 10.0) -> Any:
        import json

        if self.closed.is_set():
            raise ConnectionError("Conexión con Cortex cerrada")
        rid = self._next_id
        self._next_id += 1
        fut: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        request: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            request["params"] = params
        await self._transport.send(json.dumps(request))
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(rid, None)

    async def close(self) -> None:
        if self._reader:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._reader
        with contextlib.suppress(Exception):
            await self._transport.close()
        self.closed.set()


class EmotivCortexSource(DataSourceAdapter):
    """Fuente de datos basada en EMOTIV Cortex.

    ``source`` puede ser ``REAL_EMOTIV`` (solo cascos con ``isVirtual=False``) o
    ``VIRTUAL_DEVICE`` (solo Virtual Brainwear, ``isVirtual=True``), según el campo
    ``isVirtual`` documentado del objeto *headset*.
    """

    def __init__(
        self,
        sink: SampleSink,
        settings: Settings,
        *,
        source: DataSource = DataSource.REAL_EMOTIV,
        transport_factory: TransportFactory | None = None,
        installation_probe: Callable[[], bool | None] = detect_cortex_installation,
        poll_interval_s: float = 1.5,
    ) -> None:
        super().__init__(sink)
        if source not in (DataSource.REAL_EMOTIV, DataSource.VIRTUAL_DEVICE):
            raise ValueError("EmotivCortexSource solo admite REAL_EMOTIV o VIRTUAL_DEVICE")
        self.source = source
        self._settings = settings
        self._factory = transport_factory or websocket_transport_factory(settings.emotiv_url, settings.emotiv_ca_file)
        self._probe = installation_probe
        self._poll = poll_interval_s
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._pump_task: asyncio.Task[None] | None = None
        self._queue: asyncio.Queue[SampleBatch] = asyncio.Queue(maxsize=1000)
        self._rpc: CortexRpc | None = None
        self._token: str | None = None
        self._session_id: str | None = None
        self._cols: dict[str, list[Any]] = {}
        self._quality: dict[str, float] = {}
        self._device: DeviceInfo | None = None
        self._device_model: str | None = None
        self._restart = asyncio.Event()
        self._integration = IntegrationState.NOT_APPLICABLE
        self._connection = ConnectionState.DISCONNECTED
        self._message = "Fuente EMOTIV detenida."
        self._capabilities = self._initial_capabilities()
        self._last_sample_at: datetime | None = None
        self._last_sample_mono: float | None = None
        self._malformed = 0

    # ------------------------------------------------------------- estado/capacidades
    def _initial_capabilities(self) -> list[StreamCapability]:
        caps = [
            StreamCapability(stream=s, label=STREAM_LABELS[s], state="unknown", rate_hz=STREAM_RATES[s],
                             note="Se confirma al suscribirse")
            for s in ("pow", "eq", "dev")
            if s in self._settings.emotiv_streams
        ]
        caps.append(StreamCapability(stream="met", label="Métricas de rendimiento", state="disabled",
                                     note="Deshabilitado: métricas restringidas/licenciadas; no se usan en el MVP"))
        caps.append(StreamCapability(stream="eeg", label="EEG sin procesar", state="disabled",
                                     note="Deshabilitado: requiere licencia de pago; no se usa en el MVP"))
        return caps

    def _set_cap(self, stream: str, state: str, note: str | None = None) -> None:
        for cap in self._capabilities:
            if cap.stream == stream:
                cap.state = state  # type: ignore[assignment]
                if note is not None:
                    cap.note = note

    def status(self) -> SourceStatus:
        return SourceStatus(
            source=self.source,
            simulated=False,
            connection=self._connection,
            integration_state=self._integration,
            message=self._message,
            device=self._device,
            last_sample_at=self._last_sample_at,
            streams=[c.model_copy() for c in self._capabilities],
        )

    async def _set_state(self, integration: IntegrationState, message: str, connection: ConnectionState | None = None) -> None:
        if connection is None:
            connection = {
                IntegrationState.CONNECTED_STREAMING: ConnectionState.STREAMING,
                IntegrationState.CONNECTING: ConnectionState.CONNECTING,
                IntegrationState.AUTHORIZATION_PENDING: ConnectionState.CONNECTING,
                IntegrationState.DEVICE_DISCONNECTED: ConnectionState.SIGNAL_LOST,
            }.get(integration, ConnectionState.ERROR)
        changed = (integration, connection, message) != (self._integration, self._connection, self._message)
        self._integration, self._connection, self._message = integration, connection, message
        if changed:
            await self._sink.status_changed(self.status())

    # ------------------------------------------------------------------ ciclo de vida
    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._pump_task = asyncio.create_task(self._pump(), name="cortex-pump")
        self._task = asyncio.create_task(self._run(), name="cortex-source")
        await self._set_state(IntegrationState.CONNECTING, "Conectando con EMOTIV Cortex…")

    async def stop(self) -> None:
        self._running = False
        rpc = self._rpc
        if rpc and not rpc.closed.is_set() and self._token and self._session_id:
            with contextlib.suppress(Exception):  # cierre ordenado de la sesión (updateSession → close)
                await rpc.call(
                    "updateSession",
                    {"cortexToken": self._token, "session": self._session_id, "status": "close"},
                    timeout=3,
                )
        for task in (self._task, self._pump_task):
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        self._task = self._pump_task = None
        if rpc:
            await rpc.close()
        self._rpc = None
        self._token = self._session_id = None
        await self._set_state(IntegrationState.NOT_APPLICABLE, "Fuente EMOTIV detenida.", ConnectionState.DISCONNECTED)

    async def _pump(self) -> None:
        while True:
            batch = await self._queue.get()
            await self._sink.ingest(batch)

    async def _run(self) -> None:
        while self._running:
            try:
                terminal = await self._session()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # error inesperado: no debe tumbar el backend
                log.exception("Error en la sesión con Cortex")
                await self._set_state(IntegrationState.COMMUNICATION_ERROR, f"Error de comunicación con Cortex: {exc}")
                terminal = False
            finally:
                if self._rpc:
                    await self._rpc.close()
                    self._rpc = None
            if terminal or not self._running:
                break
            await asyncio.sleep(self._settings.emotiv_retry_delay_s)

    # ------------------------------------------------------------------ flujo oficial
    async def _session(self) -> bool:
        """Ejecuta el flujo completo. Devuelve True si no tiene sentido reintentar automáticamente."""
        s = self._settings
        if not s.has_emotiv_credentials:
            await self._set_state(
                IntegrationState.CREDENTIALS_MISSING,
                "Faltan EMOTIV_CLIENT_ID / EMOTIV_CLIENT_SECRET en el archivo .env del backend.",
            )
            return True
        if not s.emotiv_ca_file.exists():
            await self._set_state(IntegrationState.COMMUNICATION_ERROR, f"No se encuentra el certificado CA: {s.emotiv_ca_file}")
            return True

        self._reset_runtime()
        await self._set_state(IntegrationState.CONNECTING, "Conectando con EMOTIV Cortex…")
        try:
            transport = await self._factory()
        except ssl.SSLError as exc:
            await self._set_state(
                IntegrationState.COMMUNICATION_ERROR,
                f"Falló la verificación TLS con Cortex ({exc.__class__.__name__}). Revisa el certificado CA oficial.",
            )
            return True
        except (OSError, TimeoutError) as exc:
            installed = self._probe()
            if installed is False:
                await self._set_state(
                    IntegrationState.CORTEX_NOT_INSTALLED,
                    "No se detectó EMOTIV Launcher/Cortex instalado (detección heurística). Instálalo e inicia sesión.",
                )
            else:
                await self._set_state(
                    IntegrationState.CORTEX_UNAVAILABLE,
                    f"No se pudo conectar a {s.emotiv_url}. Abre EMOTIV Launcher e inténtalo de nuevo ({exc.__class__.__name__}).",
                )
            return False
        except Exception as exc:
            await self._set_state(IntegrationState.COMMUNICATION_ERROR, f"No se pudo abrir el WebSocket de Cortex: {exc}")
            return False

        rpc = CortexRpc(transport, self._on_stream, self._on_warning)
        self._rpc = rpc
        rpc.start()
        try:
            return await self._flow(rpc)
        except CortexError as exc:
            return await self._handle_cortex_error(exc)
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as exc:
            await self._set_state(IntegrationState.COMMUNICATION_ERROR, f"Se perdió la comunicación con Cortex: {exc}")
            return False

    def _reset_runtime(self) -> None:
        self._token = None
        self._session_id = None
        self._cols = {}
        self._quality = {}
        self._restart.clear()
        self._last_sample_at = None
        self._last_sample_mono = None
        self._capabilities = self._initial_capabilities()

    async def _handle_cortex_error(self, exc: CortexError) -> bool:
        if exc.code == ERR_INVALID_CLIENT_CREDENTIALS:
            await self._set_state(IntegrationState.CREDENTIALS_INVALID, "Cortex rechazó el Client ID / Client Secret.")
            return True
        if exc.code == ERR_NOT_APPROVED_IN_LAUNCHER:
            await self._set_state(IntegrationState.AUTHORIZATION_PENDING, "Aprueba la aplicación en EMOTIV Launcher.")
            return False
        if exc.code == ERR_HEADSET_UNAVAILABLE:
            await self._set_state(IntegrationState.DEVICE_DISCONNECTED, "El casco no está disponible (apagado o fuera de alcance).")
            return False
        await self._set_state(IntegrationState.COMMUNICATION_ERROR, f"Cortex devolvió un error: {exc.message} (código {exc.code})")
        return False

    async def _flow(self, rpc: CortexRpc) -> bool:
        s = self._settings
        creds = {"clientId": s.emotiv_client_id, "clientSecret": s.emotiv_client_secret.get_secret_value()}

        with contextlib.suppress(CortexError):  # informativo; no bloquea el flujo
            await rpc.call("getCortexInfo")

        # 1) Derechos de acceso → autorización
        access = await rpc.call("hasAccessRight", creds)
        if not access.get("accessGranted"):
            access = await rpc.call("requestAccess", creds)
            while not access.get("accessGranted"):
                await self._set_state(
                    IntegrationState.AUTHORIZATION_PENDING,
                    access.get("message") or "Autorización pendiente: aprueba la aplicación en EMOTIV Launcher.",
                )
                await asyncio.sleep(self._poll)
                if not self._running or rpc.closed.is_set():
                    return False
                access = await rpc.call("hasAccessRight", creds)
        auth = await rpc.call("authorize", creds)
        self._token = auth["cortexToken"]

        # 2) Dispositivos
        headset = await self._find_headset(rpc)
        if headset is None:
            return False
        headset = await self._ensure_connected(rpc, headset)
        if headset is None:
            return False

        # 3) Sesión y suscripción (status "open": pow/eq/dev no requieren sesión activa según la tabla de disponibilidad)
        created = await rpc.call("createSession", {"cortexToken": self._token, "headset": headset["id"], "status": "open"})
        self._session_id = created["id"]
        sub = await rpc.call(
            "subscribe", {"cortexToken": self._token, "session": self._session_id, "streams": list(s.emotiv_streams)}
        )
        for item in sub.get("success", []):
            self._cols[item["streamName"]] = item["cols"]
            self._set_cap(item["streamName"], "available", None)
        for item in sub.get("failure", []):
            self._set_cap(item["streamName"], "not_authorized", f"{item.get('message', 'Flujo no autorizado')} (código {item.get('code')})")
        if "pow" not in self._cols:
            await self._set_state(
                IntegrationState.STREAM_NOT_AUTHORIZED,
                "Cortex no autorizó el flujo 'pow' (potencia de bandas). Revisa la licencia/permisos de la cuenta EMOTIV.",
            )
            return True
        await self._set_state(IntegrationState.CONNECTING, "Suscrito a los flujos; esperando muestras…")

        # 4) Esperar eventos hasta cierre/restart/stop, vigilando que sigan llegando datos
        while self._running:
            closed = asyncio.create_task(rpc.closed.wait())
            restart = asyncio.create_task(self._restart.wait())
            done, pending = await asyncio.wait({closed, restart}, timeout=2.0, return_when=asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()
            if closed in done:
                await self._set_state(IntegrationState.COMMUNICATION_ERROR, "Se cerró la conexión con Cortex.")
                return False
            if restart in done:
                return False  # el mensaje de estado ya lo fijó la advertencia
            await self._check_stale()
        return True

    async def _find_headset(self, rpc: CortexRpc) -> dict[str, Any] | None:
        s = self._settings
        want_virtual = self.source == DataSource.VIRTUAL_DEVICE
        with contextlib.suppress(CortexError):
            await rpc.call("controlDevice", {"command": "refresh"})
        deadline = time.monotonic() + s.emotiv_discovery_timeout_s
        while True:
            headsets = await rpc.call("queryHeadsets", {})
            candidates = [h for h in headsets if bool(h.get("isVirtual")) == want_virtual]
            if s.emotiv_headset_id:
                candidates = [h for h in candidates if h.get("id") == s.emotiv_headset_id]
            if candidates:
                candidates.sort(key=lambda h: h.get("status") != "connected")
                return candidates[0]
            if time.monotonic() >= deadline or not self._running:
                kind = "dispositivo virtual (Virtual Brainwear)" if want_virtual else "casco físico"
                await self._set_state(
                    IntegrationState.DEVICE_NOT_FOUND,
                    f"No se encontró ningún {kind}. Enciéndelo / créalo en EMOTIV Launcher y reintenta.",
                )
                return None
            await asyncio.sleep(self._poll)

    async def _ensure_connected(self, rpc: CortexRpc, headset: dict[str, Any]) -> dict[str, Any] | None:
        self._remember_device(headset)
        if headset.get("status") == "discovered":
            await rpc.call("controlDevice", {"command": "connect", "headset": headset["id"]})
        deadline = time.monotonic() + max(self._settings.emotiv_discovery_timeout_s, 5.0)
        current = headset
        while current.get("status") != "connected":
            if time.monotonic() >= deadline or not self._running:
                await self._set_state(IntegrationState.DEVICE_DISCONNECTED, "No se pudo conectar el casco (¿apagado o fuera de alcance?).")
                return None
            await asyncio.sleep(self._poll)
            found = await rpc.call("queryHeadsets", {"id": headset["id"]})
            if found:
                current = found[0]
        self._remember_device(current)
        return current

    def _remember_device(self, headset: dict[str, Any]) -> None:
        hid = str(headset.get("id", ""))
        mode = (headset.get("settings") or {}).get("mode")
        model = hid.split("-")[0] if "-" in hid else (mode or None)
        self._device_model = model
        self._device = DeviceInfo(
            id=hid or None,
            model=model,
            is_virtual=headset.get("isVirtual"),
            connected_by=headset.get("connectedBy"),
            firmware=headset.get("firmware"),
            sensors=list(headset.get("sensors") or []),
        )

    # ------------------------------------------------------------------ callbacks
    def _on_warning(self, warning: dict[str, Any]) -> None:
        code = warning.get("code")
        msg = str(warning.get("message", ""))
        loop = asyncio.get_running_loop()
        if code in (WARN_CORTEX_STOP_ALL_STREAMS, WARN_CORTEX_CLOSE_SESSION):
            loop.create_task(self._set_state(IntegrationState.DEVICE_DISCONNECTED, "Cortex cerró la sesión de datos."))
            self._restart.set()
        elif code in (WARN_HEADSET_DISCONNECTED_TIMEOUT, WARN_HEADSET_CANNOT_CONNECT_TIMEOUT):
            loop.create_task(self._set_state(IntegrationState.DEVICE_DISCONNECTED, "El casco se desconectó (tiempo de espera de Cortex)."))
            self._restart.set()
        elif code == WARN_ACCESS_RIGHT_REJECTED:
            loop.create_task(self._set_state(IntegrationState.AUTHORIZATION_PENDING, "Rechazaste la aplicación en EMOTIV Launcher; vuelve a intentarlo."))
        else:
            log.debug("Advertencia de Cortex %s: %s", code, msg)

    def _on_stream(self, msg: dict[str, Any]) -> None:
        time_s = msg.get("time")
        src, model = self.source, self._device_model
        try:
            if "pow" in msg and "pow" in self._cols:
                samples = normalize_pow(self._cols["pow"], msg["pow"], time_s, src, model, self._quality)
            elif "eq" in msg and "eq" in self._cols:
                samples = normalize_eq(self._cols["eq"], msg["eq"], time_s, src, model)
                for sm in samples:
                    if sm.metric == "sensor_quality" and sm.sensor and sm.value is not None:
                        self._quality[sm.sensor] = sm.value
            elif "dev" in msg and "dev" in self._cols:
                samples = normalize_dev(self._cols["dev"], msg["dev"], time_s, src, model)
                for sm in samples:
                    if sm.metric == "battery_percent" and sm.value is not None and self._device:
                        self._device.battery_percent = sm.value
            else:
                return
        except MalformedSampleError as exc:
            self._malformed += 1
            log.warning("Muestra descartada: %s", exc)
            return
        if not samples:
            return
        self._last_sample_at = utcnow()
        self._last_sample_mono = time.monotonic()
        batch = SampleBatch(timestamp=samples[0].timestamp, source=src, device_model=model, samples=samples)
        try:
            self._queue.put_nowait(batch)
        except asyncio.QueueFull:
            log.warning("Cola de muestras llena: se descarta un lote")
        if self._integration != IntegrationState.CONNECTED_STREAMING or self._connection != ConnectionState.STREAMING:
            asyncio.get_running_loop().create_task(
                self._set_state(IntegrationState.CONNECTED_STREAMING, "Conectado y recibiendo datos de EMOTIV Cortex.")
            )

    async def _check_stale(self) -> None:
        if self._last_sample_mono is None or self._integration != IntegrationState.CONNECTED_STREAMING:
            return
        if time.monotonic() - self._last_sample_mono > STALE_AFTER_S:
            await self._set_state(
                IntegrationState.CONNECTED_STREAMING,
                "Cortex está conectado pero no llegan muestras recientes.",
                ConnectionState.SIGNAL_LOST,
            )
