"""PIT 读取：as-of（知识时间过滤 + 每键最新版本）与 latest。

另提供 :func:`cached_frame`：按 PIT 键缓存 DataFrame 结果（L1/L2，fail-open）。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pandas as pd
from sqlalchemy import Select, Table, func, select

if TYPE_CHECKING:  # 避免 storage → cache 的运行时耦合
    from fin_data_platform.cache import LayeredCache


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
    filters: Sequence[Any] = (),
) -> Select[Any]:
    """返回 ``knowledge_time <= as_of`` 且每个**业务键**取最新版本的查询。

    ``key_columns`` 为业务键（``business_key``；不含 knowledge_time/version），
    用于版本分组——不能使用物理键（物理键含版本维度）。
    """
    rank = _ranked(table, key_columns, knowledge_column, version_column)
    statement = select(*table.c, rank).where(table.c[knowledge_column] <= as_of)
    if filters:
        statement = statement.where(*filters)
    subquery = statement.subquery()
    return select(
        *[subquery.c[column.name] for column in table.c]
    ).where(subquery.c._rank == 1)


def latest_query(
    table: Table,
    *,
    key_columns: Sequence[str],
    knowledge_column: str = "knowledge_time",
    version_column: str = "version",
    filters: Sequence[Any] = (),
) -> Select[Any]:
    """返回每个**业务键**的最新版本（读侧派生，不落列）。"""
    rank = _ranked(table, key_columns, knowledge_column, version_column)
    statement = select(*table.c, rank)
    if filters:
        statement = statement.where(*filters)
    subquery = statement.subquery()
    return select(
        *[subquery.c[column.name] for column in table.c]
    ).where(subquery.c._rank == 1)


def cached_frame(
    cache: LayeredCache,
    key: str,
    loader: Callable[[], pd.DataFrame],
    *,
    ttl: float | None = None,
) -> pd.DataFrame:
    """按缓存键读取 DataFrame；未命中时执行 ``loader`` 并回填（fail-open）。

    键由调用方（消费层）用 ``cache.build_key(domain, panel, as_of=..., params=...)``
    构造，保证 PIT 语义与域代际正确。
    """
    value = cache.get_or_load(key, loader, ttl=ttl)
    if not isinstance(value, pd.DataFrame):
        raise TypeError(f"缓存值不是 DataFrame: {type(value).__name__}")
    return value
