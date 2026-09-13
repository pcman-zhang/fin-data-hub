"""PIT 读取：as-of（知识时间过滤 + 每键最新版本）与 latest。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, Table, func, select


def _ranked(
    table: Table, key_columns: Sequence[str], knowledge_column: str, version_column: str
):
    rank = (
        func.row_number()
        .over(
            partition_by=[table.c[name] for name in key_columns],
            order_by=[
                table.c[knowledge_column].desc(),
                table.c[version_column].desc(),
            ],
        )
        .label("_rank")
    )
    return rank


def as_of_query(
    table: Table,
    *,
    as_of: datetime,
    key_columns: Sequence[str],
    knowledge_column: str = "knowledge_time",
    version_column: str = "version",
) -> Select[Any]:
    """返回 ``knowledge_time <= as_of`` 且每个**业务键**取最新版本的查询。

    ``key_columns`` 为业务键（``business_key``；不含 knowledge_time/version），
    用于版本分组——不能使用物理键（物理键含版本维度）。
    """
    rank = _ranked(table, key_columns, knowledge_column, version_column)
    subquery = (
        select(*table.c, rank)
        .where(table.c[knowledge_column] <= as_of)
        .subquery()
    )
    return select(
        *[subquery.c[column.name] for column in table.c]
    ).where(subquery.c._rank == 1)


def latest_query(
    table: Table,
    *,
    key_columns: Sequence[str],
    knowledge_column: str = "knowledge_time",
    version_column: str = "version",
) -> Select[Any]:
    """返回每个**业务键**的最新版本（读侧派生，不落列）。"""
    rank = _ranked(table, key_columns, knowledge_column, version_column)
    subquery = select(*table.c, rank).subquery()
    return select(
        *[subquery.c[column.name] for column in table.c]
    ).where(subquery.c._rank == 1)
