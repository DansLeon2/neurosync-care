"""Local browser QA. Starts isolated services and closes every spawned process."""
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request
import urllib.error
import uuid

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".tmp" / ("uiqa-" + uuid.uuid4().hex[:8])
OUT.mkdir(parents=True)
processes = []
handles = []
errors = []
def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
backend_port, frontend_port, debug_port = port(), port(), port()
def get(url):
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.load(response)
def wait_http(url):
    end = time.monotonic() + 25
    while time.monotonic() < end:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200: return
        except Exception: pass
        time.sleep(.15)
    raise AssertionError("Service did not start: " + url)
def launch(args, cwd, env=None):
    handle = (OUT / ("process-" + str(len(handles)) + ".log")).open("w", encoding="utf-8")
    handles.append(handle)
    child = subprocess.Popen(args, cwd=cwd, env=env, stdout=handle, stderr=handle, creationflags=subprocess.CREATE_NO_WINDOW)
    processes.append(child)
    return child
try:
    env = os.environ.copy()
    env["NEUROSYNC_DATABASE_URL"] = "sqlite:///" + (OUT / "qa.db").as_posix()
    env["NEUROSYNC_CORS_ORIGINS"] = json.dumps(["http://127.0.0.1:" + str(frontend_port)])
    env["EMOTIV_CLIENT_ID"] = ""
    env["EMOTIV_CLIENT_SECRET"] = ""
    backend = launch([str(ROOT / "backend/.venv/Scripts/python.exe"), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(backend_port)], ROOT / "backend", env)
    env["VITE_API_BASE"] = "http://127.0.0.1:" + str(backend_port)
    env["VITE_WS_URL"] = "ws://127.0.0.1:" + str(backend_port) + "/ws/stream"
    launch([shutil.which("node"), str(ROOT / "frontend/node_modules/vite/bin/vite.js"), "--host", "127.0.0.1", "--port", str(frontend_port), "--strictPort"], ROOT / "frontend", env)
    api = "http://127.0.0.1:" + str(backend_port)
    site = "http://127.0.0.1:" + str(frontend_port)
    wait_http(api + "/api/health")
    wait_http(site)
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if not chrome.exists():
        chrome = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    launch([str(chrome), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=" + str(debug_port), "--remote-allow-origins=http://localhost:" + str(debug_port), "--user-data-dir=" + str(OUT / "browser"), "about:blank"], ROOT)
    debug = "http://127.0.0.1:" + str(debug_port)
    wait_http(debug + "/json/version")
    target = next(item for item in get(debug + "/json") if item["type"] == "page")
    with connect(target["webSocketDebuggerUrl"], origin="http://localhost:" + str(debug_port), max_size=20_000_000) as ws:
        next_id = 0
        def call(method, params=None):
            global next_id
            next_id += 1
            request_id = next_id
            ws.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
            while True:
                result = json.loads(ws.recv(timeout=15))
                if result.get("method") == "Runtime.exceptionThrown":
                    errors.append(result["params"]["exceptionDetails"])
                if result.get("id") == request_id:
                    if "error" in result: raise AssertionError(result["error"])
                    return result.get("result", {})
        def evaluate(expression):
            result = call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
            if "exceptionDetails" in result: raise AssertionError(result["exceptionDetails"])
            return result.get("result", {}).get("value")
        def wait(expression, timeout=20):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                if evaluate(expression): return
                time.sleep(.12)
            raise AssertionError("Timed out: " + expression + "\n" + str(evaluate("document.body.innerText")))
        def text_contains(value):
            return "document.body.textContent.includes(" + json.dumps(value) + ")"
        def click(value):
            expression = "(() => { const button = [...document.querySelectorAll('button')].find(item => item.textContent.trim().includes(" + json.dumps(value) + ") && !item.disabled); if (!button) throw new Error('Button missing'); button.click(); return true; })()"
            return evaluate(expression)
        def screenshot(name):
            result = call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            (OUT / name).write_bytes(base64.b64decode(result["data"]))
        call("Page.enable")
        call("Runtime.enable")
        call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
        call("Page.navigate", {"url": site})
        wait(text_contains("Un paso a la vez."))
        wait("!document.querySelector('.app-header button').disabled")
        screenshot("desktop.png")
        call("Emulation.setDeviceMetricsOverride", {"width": 375, "height": 900, "deviceScaleFactor": 1, "mobile": True})
        assert evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile overflow"
        screenshot("mobile.png")
        click("Nueva sesión")
        wait("document.querySelector('dialog').open")
        assert evaluate("[...document.querySelectorAll('dialog input[type=checkbox]')].every(item => !item.checked)"), "Preselected consent or quick mode"
        assert evaluate("document.querySelectorAll('dialog .rating [aria-pressed=true]').length") == 0
        evaluate("document.querySelector('dialog details').open = true")
        evaluate("document.querySelectorAll('dialog input[type=checkbox]')[1].click()")
        screenshot("mobile-prepare.png")
        click("Comenzar sesión")
        wait(text_contains("Comienza con una pausa."))
        sid = get(api + "/api/sessions/active")["id"]
        detail = get(api + "/api/sessions/" + str(sid))
        assert detail["self_reports"] == [], "Fabricated initial report"
        wait(text_contains("Continúa con operaciones sencillas."), 16)
        call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
        click("Comenzar operaciones")
        wait("document.querySelector('#math-answer') && !document.querySelector('#math-answer').disabled")
        equation = evaluate("document.querySelector('.equation').textContent")
        assert equation.count("= ?") == 1
        left, op, right = equation.split()[:3]
        expected = int(left) + int(right) if op == "+" else int(left) - int(right) if op == "-" else int(left) * int(right)
        evaluate("document.querySelector('#math-answer').focus()")
        call("Input.insertText", {"text": str(expected)})
        assert evaluate("document.querySelector('#math-answer').value") == str(expected), "Input did not receive the expected answer"
        screenshot("math-input.png")
        for _ in range(2):
            call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "text": "\r", "unmodifiedText": "\r"})
            call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
        wait(text_contains("Correcto."))
        assert len(get(api + "/api/sessions/" + str(sid))["answers"]) == 1
        screenshot("math.png")
        wait(text_contains("¿Cuánta tensión percibes ahora?"), 16)
        assert evaluate("document.querySelector('#math-answer') === null"), "Math did not close at deadline"
        evaluate("document.querySelectorAll('.rating button')[3].click()")
        click("Guardar y continuar")
        wait(text_contains("Ahora, baja el ritmo."))
        click("Comenzar pausa")
        wait(text_contains("Pausar guía"))
        click("Pausar guía")
        wait(text_contains("el registro EEG de esta fase continúa"))
        click("Continuar guía")
        click("Terminar y continuar")
        wait(text_contains("Antes de ver tus resultados"))
        evaluate("document.querySelectorAll('.rating button')[2].click()")
        click("Guardar y continuar")
        wait(text_contains("Sesión completada"))
        assert get(api + "/api/sessions") == [], "Temporary session leaked into history"
        summary = get(api + "/api/sessions/" + str(sid) + "/summary")
        assert summary["math"]["n_correct"] == 1 and summary["math"]["n_questions"] == 1
        screenshot("results.png")
        click("Cerrar resultados y descartar")
        wait(text_contains("Conoce tu actividad."))
        end = time.monotonic() + 5
        while time.monotonic() < end:
            try: get(api + "/api/sessions/" + str(sid))
            except urllib.error.HTTPError as exc:
                assert exc.code == 404
                break
            time.sleep(.1)
        else: raise AssertionError("Temporary session was not discarded")
        click("Nueva sesión")
        wait("document.querySelector('dialog').open")
        evaluate("document.querySelectorAll('dialog input[type=checkbox]')[0].click()")
        evaluate("document.querySelectorAll('dialog input[type=checkbox]')[1].click()")
        click("Comenzar sesión")
        wait(text_contains("Comienza con una pausa."))
        click("Detener sesión")
        wait(text_contains("Sesión interrumpida"))
        saved = get(api + "/api/sessions")
        assert len(saved) == 1 and saved[0]["status"] == "ABORTED"
        backend.terminate()
        backend.wait(timeout=5)
        wait(text_contains("Sin conexión al servidor"))
        assert not errors, errors
        print(json.dumps({"result": "passed", "checks": ["desktop", "mobile-375", "modal-defaults", "guided-flow", "double-enter", "math-deadline", "calm-pause", "temporary-discard", "saved-interruption", "server-disconnect", "no-runtime-exceptions"], "screenshots": str(OUT)}, ensure_ascii=False), flush=True)
finally:
    for child in reversed(processes):
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: child.kill()
    for handle in handles: handle.close()
