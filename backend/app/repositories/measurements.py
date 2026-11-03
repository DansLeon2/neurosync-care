"""Acceso a datos: mediciones agregadas."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.models.tables import MeasurementRow

COLUMNS = [
    "id", "phase_id", "timestamp", "source", "stream", "sensor", "metric", "value", "unit", "valid",
    "n_samples", "n_missing", "quality",
]


class MeasurementRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_insert(self, rows: Iterable[dict[str, Any]]) -> int:
        data = list(rows)
        if data:
            self.db.execute(insert(MeasurementRow), data)
        return len(data)

    def count(self, session_id: int) -> int:
        stmt = select(func.count(MeasurementRow.id)).where(MeasurementRow.session_id == session_id)
        return int(self.db.execute(stmt).scalar_one())

    def dataframe(self, session_id: int) -> pd.DataFrame:
        stmt = select(*[getattr(MeasurementRow, c) for c in COLUMNS]).where(MeasurementRow.session_id == session_id)
        rows = self.db.execute(stmt.order_by(MeasurementRow.timestamp, MeasurementRow.id)).all()
        df = pd.DataFrame(rows, columns=COLUMNS)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df

