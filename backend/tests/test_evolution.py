"""Regresiones de compatibilidad, concurrencia y piloto de código."""
import asyncio
import csv
from datetime import datetime, timedelta
import io
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from app.database.core import init_db, make_engine, make_session_factory, session_scope
from app.models.tables import MeasurementRow, SelfReportRow, SessionRow
from app.repositories.measurements import MeasurementRepository
from app.schemas.enums import DataSource, Stream
from app.schemas.samples import Sample, SampleBatch, utcnow
from app.services.hub import StreamHub


def coding_session(client, task_id=None):
    task = client.get('/api/coding/tasks').json()[0]
    sid = client.post('/api/sessions', json={'consent_storage': True, 'test_mode': True, 'activity_kind': 'CODING'}).json()['id']
    response = client.post(f'/api/sessions/{sid}/phases', json={'kind': 'CODING', 'detail': task_id or task['id']})
    return sid, task, response


def test_old_database_migration_preserves_rows_and_is_idempotent(tmp_path):
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.executescript('''
        CREATE TABLE sessions (id INTEGER PRIMARY KEY, started_at DATETIME NOT NULL, ended_at DATETIME,
            data_source VARCHAR(20) NOT NULL, status VARCHAR(12) NOT NULL, consent_storage BOOLEAN NOT NULL,
            device_model VARCHAR(40), test_mode BOOLEAN NOT NULL);
        CREATE TABLE self_reports (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, phase_id INTEGER,
            moment VARCHAR(12) NOT NULL, tension INTEGER NOT NULL, difficulty INTEGER, comfort INTEGER,
            note VARCHAR(300), timestamp DATETIME NOT NULL);
        INSERT INTO sessions VALUES (1,'2020-01-01 00:00:00.000000',NULL,'SIMULATED','COMPLETED',1,NULL,0);
        INSERT INTO self_reports VALUES (1,1,NULL,'INITIAL',4,NULL,NULL,NULL,'2020-01-01 00:00:00.000000');
        ''')
    engine = make_engine('sqlite:///' + path.as_posix())
    try:
        init_db(engine)
        init_db(engine)
        with session_scope(make_session_factory(engine)) as db:
            assert db.get(SessionRow, 1).activity_kind == 'MATH'
            report = db.get(SelfReportRow, 1)
            assert report.tension == 4 and report.effort is None
    finally:
        engine.dispose()


def test_hub_thread_delivery_snapshots_and_bounded_queue():
    async def scenario():
        hub = StreamHub(queue_size=2)
        queue = hub.subscribe()
        message = {'value': {'alpha': 2}}
        await asyncio.to_thread(hub.broadcast, message)
        message['value']['alpha'] = 99
        assert (await asyncio.wait_for(queue.get(), 1))['value']['alpha'] == 2
        for value in range(10):
            hub.broadcast({'n': value})
        assert [queue.get_nowait()['n'], queue.get_nowait()['n']] == [8, 9]
        hub.unsubscribe(queue)
        hub.broadcast({'n': 11})
        assert queue.empty() and hub.client_count == 0
    asyncio.run(scenario())


def test_recorder_keeps_windows_until_commit_succeeds(client, monkeypatch):
    ctx = client.app.state.container
    client.post('/api/sessions', json={'consent_storage': True})
    now = utcnow()
    batch = SampleBatch(timestamp=now, source=DataSource.SIMULATED, samples=[Sample(
        timestamp=now, source=DataSource.SIMULATED, stream=Stream.POW,
        sensor='AF3', metric='alpha', value=2, unit='u.a. (simulado)')])
    ctx.recorder.add(batch)
    original = MeasurementRepository.bulk_insert
    def fail(*args):
        raise RuntimeError('test: disk temporarily unavailable')
    monkeypatch.setattr(MeasurementRepository, 'bulk_insert', fail)
    assert ctx.recorder.flush() == 0
    assert ctx.recorder._bins
    monkeypatch.setattr(MeasurementRepository, 'bulk_insert', original)
    assert ctx.recorder.flush() == 1
    assert ctx.recorder.flush() == 0
    with session_scope(ctx.session_factory) as db:
        rows = list(db.scalars(select(MeasurementRow)))
        assert len(rows) == 1 and rows[0].value == 2 and rows[0].n_samples == 1


def test_coding_flow_and_subjective_effort_are_separate_from_eeg(client):
    sid, task, phase_response = coding_session(client)
    assert phase_response.status_code == 201
    assert 'expected' not in task and 'correct' not in task
    assert client.get('/api/sessions/active').json()['activity_kind'] == 'CODING'
    payload = {'session_id': sid, 'task_id': task['id'], 'choice': 1}
    answer = client.post('/api/coding/answers', json=payload)
    assert answer.status_code == 200 and answer.json()['correct'] is True
    assert answer.json()['elapsed_ms'] >= 0
    assert client.post('/api/coding/answers', json=payload).status_code == 409
    assert client.post('/api/math/questions', json={'session_id': sid}).status_code == 409
    report = client.post(f'/api/sessions/{sid}/self-reports', json={'moment': 'POST_CODING', 'tension': 4, 'effort': 7, 'difficulty': 3})
    assert report.status_code == 201 and report.json()['effort'] == 7
    assert client.post(f'/api/sessions/{sid}/self-reports', json={'tension': 1, 'effort': 11}).status_code == 422
    client.post(f'/api/sessions/{sid}/finish')
    summary = client.get(f'/api/sessions/{sid}/summary').json()
    assert summary['coding']['n_completed'] == 1 and summary['math'] is None
    assert summary['total_measurement_rows'] == 0  # no invented physiology
    assert len(client.get(f'/api/sessions/{sid}').json()['coding_answers']) == 1
    exported = client.get(f'/api/sessions/{sid}/export.csv?dataset=coding')
    rows = list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))))
    assert len(rows) == 1 and rows[0]['correct'] == '1'
    assert 'effort_0_10' in client.get(f'/api/sessions/{sid}/export.csv?dataset=self_reports').text


def test_coding_phase_requires_a_catalog_task(client):
    sid, _, response = coding_session(client, 'not-a-task')
    assert response.status_code == 409
    assert client.get(f'/api/sessions/{sid}').json()['session']['phases'] == []


def test_coding_without_answers_remains_an_unresolved_task(client):
    sid, _, response = coding_session(client)
    assert response.status_code == 201
    client.post(f'/api/sessions/{sid}/finish')
    summary = client.get(f'/api/sessions/{sid}/summary').json()['coding']
    assert summary['n_tasks'] == 1 and summary['n_completed'] == 0
    assert summary['n_incomplete'] == 1 and summary['n_attempts'] == 0


def test_coding_attempt_limit_and_phase_binding(client):
    sid, task, phase = coding_session(client)
    assert phase.status_code == 201
    other = client.get('/api/coding/tasks').json()[1]
    assert client.post('/api/coding/answers', json={'session_id': sid, 'task_id': other['id'], 'choice': 0}).status_code == 409
    for attempt in range(1,4):
        result = client.post('/api/coding/answers', json={'session_id': sid, 'task_id': task['id'], 'choice': 0})
        assert result.status_code == 200 and result.json()['attempt'] == attempt
    assert client.post('/api/coding/answers', json={'session_id': sid, 'task_id': task['id'], 'choice': 0}).status_code == 409
    assert client.get(f'/api/sessions/{sid}/summary').json()['coding']['n_completed'] == 0


def test_coding_deadline_is_checked_on_server(client):
    sid, task, response = coding_session(client)
    phase = response.json()
    client.app.state.container.coding._clock = lambda: datetime.fromisoformat(phase['started_at']) + timedelta(seconds=phase['planned_duration_s'])
    assert client.post('/api/coding/answers', json={'session_id': sid, 'task_id': task['id'], 'choice': 1}).status_code == 409
    assert client.get(f'/api/sessions/{sid}').json()['coding_answers'] == []


def test_browser_disconnect_does_not_finish_session(client):
    client.post('/api/simulator/start')
    sid = client.post('/api/sessions', json={}).json()['id']
    with client.websocket_connect('/ws/stream') as ws:
        assert ws.receive_json()['session']['id'] == sid
    received = client.app.state.container.pipeline.samples_received
    time.sleep(.35)
    assert client.get('/api/sessions/active').json()['id'] == sid
    assert client.app.state.container.pipeline.samples_received > received


def test_session_and_phase_creation_are_serialized(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        sessions = list(pool.map(lambda _: client.post('/api/sessions', json={}).status_code, range(2)))
    assert sorted(sessions) == [201, 409]
    sid = client.get('/api/sessions/active').json()['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        phases = list(pool.map(lambda _: client.post(f'/api/sessions/{sid}/phases', json={'kind':'BASELINE'}).status_code, range(2)))
    assert sorted(phases) == [201, 409]
    assert len(client.get(f'/api/sessions/{sid}').json()['session']['phases']) == 1
