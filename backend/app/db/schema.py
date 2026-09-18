from __future__ import annotations

import logging

from sqlalchemy import inspect, text

log = logging.getLogger("APP")


def ensure_schema(engine) -> None:
    """Add Trust Pay columns to existing payments tables (create_all does not ALTER)."""
    insp = inspect(engine)
    if "payments" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("payments")}
    pg = engine.dialect.name == "postgresql"
    additions = [
        ("public_id", "VARCHAR(16)"),
        ("fee", "NUMERIC(18,2) DEFAULT 0"),
        ("total", "NUMERIC(18,2) DEFAULT 0"),
        ("currency", "VARCHAR(8) DEFAULT 'RUB'"),
        ("credited", "BOOLEAN DEFAULT FALSE" if pg else "INTEGER DEFAULT 0"),
        ("confirmed_by", "INTEGER"),
        ("paid_at", "TIMESTAMP"),
        ("expires_at", "TIMESTAMP"),
    ]
    with engine.begin() as conn:
        for name, typ in additions:
            if name in cols:
                continue
            conn.execute(text(f"ALTER TABLE payments ADD COLUMN {name} {typ}"))
            log.info("schema: added payments.%s", name)
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_public_id ON payments (public_id)"))
