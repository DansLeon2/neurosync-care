"""Pruebas de la API REST: sesiones, autoevaluaciones, matemáticas, estadísticas, exportación."""

from __future__ import annotations

import csv
import io
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def select_sim(client: TestClient, scenario: str = "ACTIVITY_DEMO") -> None:
    client.put("/api/simulator/config", json={"scenario": scenario, "seed": 11})
    r = client.post("/api/simulator/start")
    assert r.status_code == 200 and r.json()["source"] == "SIMULATED"


def run_phase(client: TestClient, sid: int, kind: str, seconds: float = 1.3) -> dict:
    ph = client.post(f"/api/sessions/{sid}/phases", json={"kind": kind, "planned_duration_s": 2})
    assert ph.status_code == 201, ph.text
    time.sleep(seconds)
    ended = client.post(f"/api/sessions/{sid}/phases/{ph.json()['id']}/end")
    assert ended.status_code == 200
    return ended.json()


def test_health_and_protocol(client: TestClient) -> None:
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["database"] == "ok" and h["medical_device"] is False
    proto = client.get("/api/protocol").json()
    assert [p["key"] for p in proto["phases"]][0] == "intro"
    assert "No es un dispositivo médico" in proto["disclaimer"]


def test_source_status_default_is_disconnected(client: TestClient) -> None:
    st = client.get("/api/source/status").json()
    assert st["source"] == "DISCONNECTED" and st["connection"] == "DISCONNECTED" and st["simulated"] is False


def test_openapi_documents_the_api(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "/api/sessions" in spec["paths"] and "/api/simulator/disconnect" in spec["paths"]


def test_full_session_flow_with_simulator(client: TestClient) -> None:
    select_sim(client)
    caps = client.get("/api/source/capabilities").json()
    assert {c["stream"]: c["state"] for c in caps}["pow"] == "available"

    sess = client.post("/api/sessions", json={"consent_storage": True, "test_mode": True})
    assert sess.status_code == 201
    sid = sess.json()["id"]
    assert sess.json()["data_source"] == "SIMULATED" and sess.json()["status"] == "ACTIVE"
    assert client.get("/api/sessions/active").json()["id"] == sid
    assert client.post("/api/sessions", json={"consent_storage": True}).status_code == 409  # solo una activa

    r = client.post(f"/api/sessions/{sid}/self-reports", json={"moment": "INITIAL", "tension": 6})
    assert r.status_code == 201 and r.json()["tension"] == 6

    run_phase(client, sid, "BASELINE")

    math_phase = client.post(f"/api/sessions/{sid}/phases", json={"kind": "MATH", "detail": "EASY"}).json()
    q = client.post("/api/math/questions", json={"difficulty": "EASY", "session_id": sid}).json()
    assert q["recorded"] is True and "expected" not in str(q)
    a, op, b = q["text"].split(" ")[:3]
    expected = int(a) + int(b) if op == "+" else int(a) - int(b)
    ans = client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": expected}).json()
    assert ans["result"] == "CORRECT" and ans["expected_answer"] == expected and ans["recorded"] is True
    q2 = client.post("/api/math/questions", json={"difficulty": "EASY", "session_id": sid}).json()
    wrong = client.post("/api/math/answers", json={"question_id": q2["question_id"], "answer": -999}).json()
    assert wrong["result"] == "INCORRECT"
    q3 = client.post("/api/math/questions", json={"difficulty": "EASY", "session_id": sid}).json()
    skipped = client.post("/api/math/answers", json={"question_id": q3["question_id"], "answer": None}).json()
    assert skipped["result"] == "SKIPPED"
    time.sleep(1.3)
    client.post(f"/api/sessions/{sid}/phases/{math_phase['id']}/end")

    client.post(f"/api/sessions/{sid}/self-reports", json={"moment": "POST_MATH", "tension": 7, "difficulty": 5})
    run_phase(client, sid, "REGULATION")
    client.post(f"/api/sessions/{sid}/self-reports", json={"moment": "FINAL", "tension": 3, "comfort": 8})

    fin = client.post(f"/api/sessions/{sid}/finish")
    assert fin.status_code == 200 and fin.json()["status"] == "COMPLETED" and fin.json()["ended_at"]
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 409  # ya finalizada

    detail = client.get(f"/api/sessions/{sid}").json()
    assert [p["kind"] for p in detail["session"]["phases"]] == ["BASELINE", "MATH", "REGULATION"]
    assert len(detail["answers"]) == 3 and len(detail["self_reports"]) == 3
    assert {e["event"] for e in detail["events"]} >= {"SESSION_STARTED", "SESSION_COMPLETED"}

    summary = client.get(f"/api/sessions/{sid}/summary").json()
    assert summary["simulated_data"] is True and summary["mixed_sources"] is False
    assert summary["math"]["n_questions"] == 3 and summary["math"]["n_correct"] == 1
    assert summary["math"]["accuracy_pct"] == 33.3 and summary["math"]["n_skipped"] == 1
    changes = {c["label"]: c["change"] for c in summary["tension_changes"]}
    assert changes["Inicial → final"] == -3
    assert {p["kind"] for p in summary["phases"]} == {"BASELINE", "MATH", "REGULATION"}
    base = next(p for p in summary["phases"] if p["kind"] == "BASELINE")
    alpha = next(b for b in base["bands"] if b["band"] == "alpha")
    assert base["sufficient"] and alpha["n_valid_samples"] > 20 and alpha["mean"] > 0

    cmp = client.get(f"/api/sessions/{sid}/compare", params={"a": "BASELINE", "b": "REGULATION"}).json()
    assert cmp["available"] is True and len(cmp["deltas"]) == 5
    assert "No son inferencias" in cmp["note"] or "descriptivas" in cmp["note"]

    ts = client.get(f"/api/sessions/{sid}/timeseries").json()
    assert ts["simulated_data"] is True and len(ts["points"]) >= 3 and ts["unit"].startswith("u.a.")

    hist = client.get("/api/sessions").json()
    assert len(hist) == 1 and hist[0]["math_total"] == 3 and hist[0]["tension_initial"] == 6 and hist[0]["tension_final"] == 3
    assert hist[0]["activities"] == ["BASELINE", "MATH", "REGULATION"]


def test_csv_export(client: TestClient) -> None:
    select_sim(client)
    sid = client.post("/api/sessions", json={"consent_storage": True}).json()["id"]
    run_phase(client, sid, "BASELINE", 1.5)
    client.post(f"/api/sessions/{sid}/self-reports", json={"moment": "INITIAL", "tension": 4})
    client.post(f"/api/sessions/{sid}/finish")

    r = client.get(f"/api/sessions/{sid}/export.csv", params={"dataset": "measurements"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text.lstrip("\ufeff"))))
    assert rows and rows[0]["source"] == "SIMULATED" and rows[0]["phase_kind"] in ("BASELINE", "")
    assert any(row["stream"] == "pow" and row["metric"] == "alpha" for row in rows)

    summary = list(csv.DictReader(io.StringIO(client.get(f"/api/sessions/{sid}/export.csv", params={"dataset": "summary"}).text.lstrip("\ufeff"))))
    assert {r["band"] for r in summary} == {"theta", "alpha", "low_beta", "high_beta", "gamma"}
    sr = client.get(f"/api/sessions/{sid}/export.csv", params={"dataset": "self_reports"}).text
    assert "INITIAL" in sr
    assert client.get(f"/api/sessions/{sid}/export.csv", params={"dataset": "nope"}).status_code == 404
    assert client.get("/api/sessions/9999/export.csv").status_code == 404


def test_invalid_inputs_and_missing_resources(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"consent_storage": True}).json()["id"]
    assert client.post(f"/api/sessions/{sid}/self-reports", json={"moment": "INITIAL", "tension": 11}).status_code == 422
    assert client.post(f"/api/sessions/{sid}/self-reports", json={"moment": "INITIAL", "tension": -1}).status_code == 422
    assert client.post(f"/api/sessions/{sid}/self-reports", json={"moment": "BAD", "tension": 5}).status_code == 422
    assert client.post(f"/api/sessions/{sid}/phases", json={"kind": "NOPE"}).status_code == 422
    assert client.post(f"/api/sessions/{sid}/phases", json={"kind": "MATH", "planned_duration_s": -5}).status_code == 422
    assert client.post("/api/sessions/9999/finish").status_code == 404
    assert client.get("/api/sessions/9999").status_code == 404
    assert client.post("/api/sessions/9999/self-reports", json={"moment": "INITIAL", "tension": 1}).status_code == 404
    assert client.post(f"/api/sessions/{sid}/phases/9999/end").status_code == 404
    assert client.post("/api/math/answers", json={"question_id": "nope", "answer": 1}).status_code == 404
    assert client.post("/api/math/questions", json={"difficulty": "EASY", "session_id": 9999}).status_code == 404
    assert client.delete(f"/api/sessions/{sid}").status_code == 409  # activa
    assert "ya finalizó" not in client.post(f"/api/sessions/{sid}/finish").text


def test_math_practice_mode_without_session_is_not_recorded(client: TestClient) -> None:
    q = client.post("/api/math/questions", json={"difficulty": "HARD"}).json()
    assert q["recorded"] is False
    ans = client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": 0}).json()
    assert ans["recorded"] is False and ans["result"] in ("CORRECT", "INCORRECT")
    assert client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": 0}).status_code == 404


def test_difficulty_levels_generate_valid_operations(client: TestClient) -> None:
    import random

    from app.schemas.enums import MathDifficulty
    from app.services.math_service import generate_question

    rng = random.Random(0)
    for diff in MathDifficulty:
        ops = set()
        for _ in range(300):
            text, op, expected = generate_question(rng, diff)
            ops.add(op.value)
            a, sym, b = text.split(" ")[:3]
            real = {"+": int(a) + int(b), "-": int(a) - int(b), "×": int(a) * int(b)}[sym]
            assert real == expected and expected >= 0
        assert {"ADD", "SUBTRACT"} <= ops
        assert ("MULTIPLY" in ops) == (diff != MathDifficulty.EASY)


def test_source_change_during_session_requires_confirmation(client: TestClient) -> None:
    select_sim(client)
    sid = client.post("/api/sessions", json={"consent_storage": True}).json()["id"]
    blocked = client.post("/api/source/select", json={"source": "REAL_EMOTIV"})
    assert blocked.status_code == 409 and "sesión activa" in blocked.json()["detail"]
    assert client.get("/api/source/status").json()["source"] == "SIMULATED"
    forced = client.post("/api/source/select", json={"source": "DISCONNECTED", "force": True})
    assert forced.status_code == 200 and forced.json()["source"] == "DISCONNECTED"
    events = client.get(f"/api/sessions/{sid}").json()["events"]
    assert any(e["event"] == "SOURCE_CHANGED" for e in events)


def test_emotiv_source_without_credentials_gives_clear_message(client: TestClient) -> None:
    r = client.post("/api/source/select", json={"source": "REAL_EMOTIV"})
    assert r.status_code == 200
    body = r.json()
    assert body["integration_state"] == "CREDENTIALS_MISSING" and body["simulated"] is False
    assert "EMOTIV_CLIENT_ID" in body["message"]
    assert body["device"] is None
    caps = {c["stream"]: c["state"] for c in body["streams"]}
    assert caps["met"] == "disabled" and caps["eeg"] == "disabled"  # no se muestran como disponibles
    assert "secret" not in r.text.lower().replace("client_secret", "")


def test_simulator_controls(client: TestClient) -> None:
    assert client.post("/api/simulator/disconnect", json={"duration_s": 3}).status_code == 409  # simulador inactivo
    select_sim(client, "NORMAL")
    d = client.post("/api/simulator/disconnect", json={"duration_s": None}).json()
    assert d["connection"] == "SIGNAL_LOST"
    r = client.post("/api/simulator/reconnect").json()
    assert r["connection"] == "STREAMING"
    cfg = client.put("/api/simulator/config", json={"poor_sensors": ["AF3"]}).json()
    assert cfg["poor_sensors"] == ["AF3"] and cfg["scenario"] == "NORMAL"
    stopped = client.post("/api/simulator/stop").json()
    assert stopped["source"] == "DISCONNECTED"
    assert client.put("/api/simulator/config", json={"scenario": "INVALID"}).status_code == 422
    scen = client.get("/api/simulator/scenarios").json()
    assert {s["id"] for s in scen} >= {"NORMAL", "VARIABLE_POWER", "POOR_QUALITY", "TEMPORARY_DISCONNECT", "NO_OPTIONAL_METRICS"}


def test_disconnect_during_session_is_recorded_and_app_keeps_working(client: TestClient) -> None:
    select_sim(client, "NORMAL")
    sid = client.post("/api/sessions", json={"consent_storage": True}).json()["id"]
    run_phase(client, sid, "BASELINE", 1.3)
    client.post("/api/simulator/disconnect", json={"duration_s": None})
    time.sleep(0.5)
    assert client.get("/api/health").json()["status"] == "ok"
    client.post("/api/simulator/reconnect")
    time.sleep(0.4)
    client.post(f"/api/sessions/{sid}/finish")
    events = [e["event"] for e in client.get(f"/api/sessions/{sid}").json()["events"]]
    assert "SIGNAL_LOST" in events and events.count("STREAMING") >= 1


def test_insufficient_data_is_reported_not_invented(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"consent_storage": True}).json()["id"]  # sin fuente
    run_phase(client, sid, "BASELINE", 0.3)
    run_phase(client, sid, "MATH", 0.3)
    client.post(f"/api/sessions/{sid}/finish")
    cmp = client.get(f"/api/sessions/{sid}/compare", params={"a": "BASELINE", "b": "MATH"}).json()
    assert cmp["available"] is False and cmp["deltas"] == [] and "No hay datos EEG" in cmp["reason"]
    missing = client.get(f"/api/sessions/{sid}/compare", params={"a": "BASELINE", "b": "REGULATION"}).json()
    assert missing["available"] is False and "No existe la fase B" in missing["reason"]
    summary = client.get(f"/api/sessions/{sid}/summary").json()
    assert summary["math"] is None and summary["total_measurement_rows"] == 0
    assert all(p["sufficient"] is False for p in summary["phases"])


def test_delete_one_and_all_sessions(client: TestClient) -> None:
    ids = []
    for _ in range(3):
        sid = client.post("/api/sessions", json={"consent_storage": True}).json()["id"]
        client.post(f"/api/sessions/{sid}/finish")
        ids.append(sid)
    assert client.delete(f"/api/sessions/{ids[0]}").status_code == 204
    assert client.get(f"/api/sessions/{ids[0]}").status_code == 404
    assert client.delete("/api/sessions/9999").status_code == 404
    assert client.delete("/api/sessions").json() == {"deleted": 2}
    assert client.get("/api/sessions").json() == []


def test_session_without_consent_is_not_in_history_and_can_be_discarded(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"consent_storage": False}).json()["id"]
    client.post(f"/api/sessions/{sid}/finish")
    assert client.get("/api/sessions").json() == []
    assert client.get(f"/api/sessions/{sid}/summary").status_code == 200  # visible solo para mostrar resultados
    assert client.post(f"/api/sessions/{sid}/discard").json() == {"discarded": True}
    assert client.get(f"/api/sessions/{sid}").status_code == 404


def test_history_persists_after_backend_restart_and_cleanup(settings: Settings) -> None:
    with TestClient(create_app(settings)) as c1:
        saved = c1.post("/api/sessions", json={"consent_storage": True}).json()["id"]
        c1.post(f"/api/sessions/{saved}/self-reports", json={"moment": "INITIAL", "tension": 5})
        c1.post(f"/api/sessions/{saved}/finish")
        temp = c1.post("/api/sessions", json={"consent_storage": False}).json()["id"]
        c1.post(f"/api/sessions/{temp}/finish")
        orphan = c1.post("/api/sessions", json={"consent_storage": True}).json()["id"]  # queda ACTIVE
    with TestClient(create_app(settings)) as c2:  # "reinicio" del backend
        hist = {s["id"]: s for s in c2.get("/api/sessions").json()}
        assert saved in hist and hist[saved]["tension_initial"] == 5
        assert c2.get(f"/api/sessions/{temp}").status_code == 404  # sin consentimiento: purgada
        assert hist[orphan]["status"] == "ABORTED"  # sesión huérfana cerrada
        assert c2.get("/api/sessions/active").json() is None
    assert Path(settings.database_url.removeprefix("sqlite:///")).exists()


def test_cors_restricted_to_local_frontend(client: TestClient) -> None:
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers

