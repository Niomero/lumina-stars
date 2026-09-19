from __future__ import annotations

import logging

from sqlalchemy import inspect, text

log = logging.getLogger("APP")


def _add_columns(conn, insp, table: str, additions: list[tuple[str, str]]) -> None:
    if table not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    for name, typ in additions:
        if name in cols:
            continue
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
        log.info("schema: added %s.%s", table, name)


def ensure_schema(engine) -> None:
    """Add columns that create_all will not ALTER on existing databases."""
    insp = inspect(engine)
    pg = engine.dialect.name == "postgresql"
    with engine.begin() as conn:
        _add_columns(
            conn,
            insp,
            "payments",
            [
                ("public_id", "VARCHAR(16)"),
                ("fee", "NUMERIC(18,2) DEFAULT 0"),
                ("total", "NUMERIC(18,2) DEFAULT 0"),
                ("currency", "VARCHAR(8) DEFAULT 'RUB'"),
                ("credited", "BOOLEAN DEFAULT FALSE" if pg else "INTEGER DEFAULT 0"),
                ("confirmed_by", "INTEGER"),
                ("paid_at", "TIMESTAMP"),
                ("expires_at", "TIMESTAMP"),
            ],
        )
        if "payments" in insp.get_table_names():
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_public_id ON payments (public_id)"))
        _add_columns(
            conn,
            insp,
            "digital_products",
            [
                ("amount_mode", "VARCHAR(16) DEFAULT 'fixed'"),
                ("markup_percent", "NUMERIC(18,2) DEFAULT 0"),
                ("min_amount", "NUMERIC(18,2) DEFAULT 0"),
                ("max_amount", "NUMERIC(18,2) DEFAULT 0"),
            ],
        )