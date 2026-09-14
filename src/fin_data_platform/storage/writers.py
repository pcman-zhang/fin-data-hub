"""幂等写入（append-only）：``ON CONFLICT (physical_key) DO NOTHING``。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Insert, Table, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection


def append_rows(
    connection: Connection, table: Table, rows: Sequence[dict[str, Any]]
) -> int:
    """幂等追加：冲突（物理键）跳过；返回实际插入行数。

    - PostgreSQL / SQLite：``ON CONFLICT DO NOTHING``；
    - 其他方言：普通 INSERT（由调用方保证唯一性）。
    """
    if not rows:
        return 0
    dialect = connection.dialect.name
    pk_column = next(iter(table.primary_key.columns))
    statement: Insert
    if dialect == "postgresql":
        statement = (
            pg_insert(table)
            .values(list(rows))
            .on_conflict_do_nothing()
            .returning(pk_column)
        )
    elif dialect == "sqlite":
        statement = (
            sqlite_insert(table)
            .values(list(rows))
            .on_conflict_do_nothing()
            .returning(pk_column)
        )
    else:
        statement = insert(table).values(list(rows))
    result = connection.execute(statement)
    if result.returns_rows:
        return len(result.fetchall())
    return int(result.rowcount or 0)
