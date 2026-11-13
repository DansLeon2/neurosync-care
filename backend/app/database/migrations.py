"""Migraciones aditivas e idempotentes; no recrean ni vacían tablas existentes."""
from sqlalchemy import Engine, inspect, text


def migrate(engine: Engine) -> None:
    additions = {
        "sessions": {"activity_kind": "VARCHAR(16) NOT NULL DEFAULT 'MATH'"},
        "self_reports": {"effort": "INTEGER"},
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {column["name"] for column in inspect(connection).get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
