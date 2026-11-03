"""Regresiones: límites, caducidad real, fase de origen y solicitudes repetidas."""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.schemas.samples import utcnow
from app.services.math_service import QUESTION_TTL
from app.services.protocol import PROTOCOL


def start_math(client: TestClient, duration: float | None = None):
    session = client.post("/api/sessions", json={"test_mode": True}).json()
    payload = {"kind": "MATH"}
    if duration is not None:
        payload["planned_duration_s"] = duration
    phase = client.post(f"/api/sessions/{session['id']}/phases", json=payload)
    assert phase.status_code == 201, phase.text
    return session, phase.json()


def question(client, sid=None):
    response = client.post("/api/math/questions", json={"session_id": sid})
    assert response.status_code == 200, response.text
    return response.json()


def test_protocol_is_the_source_of_default_phase_durations(client):
    policy = client.get("/api/protocol").json()
    assert policy["math"]["max_questions"] == 20
    session, phase = start_math(client)
    definition = next(value for value in policy["phases"] if value["kind"] == "MATH")
    assert phase["planned_duration_s"] == definition["test_duration_s"]
    assert client.post(f"/api/sessions/{session['id']}/phases", json={"kind": "REGULATION"}).status_code == 409


def test_math_requires_an_active_math_phase(client):
    session = client.post("/api/sessions", json={}).json()
    assert client.post("/api/math/questions", json={"session_id": session["id"]}).status_code == 409
    client.post(f"/api/sessions/{session['id']}/phases", json={"kind": "BASELINE"})
    assert client.post("/api/math/questions", json={"session_id": session["id"]}).status_code == 409


def test_question_expiry_checked_when_answering_without_issuing_again(client):
    current = [utcnow()]
    client.app.state.container.math._clock = lambda: current[0]
    q = question(client)
    current[0] += QUESTION_TTL
    assert client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": 0}).status_code == 404


def test_phase_deadline_is_enforced_by_server(client):
    session, phase = start_math(client, 1)
    q = question(client, session["id"])
    from datetime import datetime
    client.app.state.container.math._clock = lambda: datetime.fromisoformat(phase["started_at"]) + timedelta(seconds=1)
    assert client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": 1}).status_code == 404
    assert client.post("/api/math/questions", json={"session_id": session["id"]}).status_code == 409
    assert client.get(f"/api/sessions/{session['id']}").json()["answers"] == []


def test_question_cannot_move_to_a_different_math_phase(client):
    session, phase = start_math(client)
    q = question(client, session["id"])
    client.post(f"/api/sessions/{session['id']}/phases/{phase['id']}/end")
    client.post(f"/api/sessions/{session['id']}/phases", json={"kind": "MATH"})
    result = client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": 1})
    assert result.status_code == 409
    assert client.get(f"/api/sessions/{session['id']}").json()["answers"] == []


def test_question_cannot_be_answered_after_session_finishes(client):
    session, _ = start_math(client)
    q = question(client, session["id"])
    client.post(f"/api/sessions/{session['id']}/finish")
    assert client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": 0}).status_code == 409


def test_pending_question_is_reused_and_answer_is_not_duplicated(client):
    session, _ = start_math(client)
    q = question(client, session["id"])
    assert question(client, session["id"])["question_id"] == q["question_id"]
    def answer():
        return client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": None}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: answer(), range(2))) == [200, 404]
    assert len(client.get(f"/api/sessions/{session['id']}").json()["answers"]) == 1


@pytest.mark.parametrize("invalid", [10000, -10000, 1.5, True, "2", "NaN"])
def test_answer_requires_a_bounded_integer(client, invalid):
    q = question(client)
    assert client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": invalid}).status_code == 422
    assert client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": None}).status_code == 200


def test_phase_question_limit_cannot_be_bypassed_with_new_requests(client):
    session, _ = start_math(client, 120)
    for index in range(PROTOCOL.math.max_questions):
        q = question(client, session["id"])
        assert q["question_number"] == index + 1
        assert client.post("/api/math/answers", json={"question_id": q["question_id"], "answer": None}).status_code == 200
    assert client.post("/api/math/questions", json={"session_id": session["id"]}).status_code == 409
    assert len(client.get(f"/api/sessions/{session['id']}").json()["answers"]) == PROTOCOL.math.max_questions


def test_pending_questions_have_a_memory_bound(client, monkeypatch):
    monkeypatch.setattr("app.services.math_service.MAX_PENDING", 2)
    question(client)
    question(client)
    assert client.post("/api/math/questions", json={}).status_code == 409


def test_math_duration_cannot_exceed_protocol_maximum(client):
    session = client.post("/api/sessions", json={}).json()
    assert client.post(f"/api/sessions/{session['id']}/phases", json={"kind": "MATH", "planned_duration_s": 121}).status_code == 409
