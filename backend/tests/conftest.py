"""Fixtures compartidas. Cada prueba usa su propia base SQLite temporal."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_settings(tmp_path: Path, **overrides) -> Settings:  # type: ignore[no-untyped-def]
    values = dict(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        emotiv_client_id="",
        emotiv_client_secret="",
        simulator_seed=7,
        persist_bin_seconds=0.3,
        min_valid_bins=2,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c

