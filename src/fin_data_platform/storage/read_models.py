"""引用注册表读模型（doc-10 §3.3 / doc-13 §1.1）。

- ``mart.entity_latest_v1``：当前态视图（每实体取 open 行最高版本）；
- ``mart.entity_asof(as_of)``：属性 as-of 表函数（PostgreSQL；知识时间 + 生效区间双维）；
- :func:`entity_asof_query`：跨方言 as-of 查询构造器（SDK 用；测试以 SQLite 验证语义）。

SDK/REST 只读 mart；视图/函数由本模块生成，迁移执行由 TASK-3.3 接入。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Engine, Select, Table, func, select, text

from fin_data_platform.registry.schema import entity

MART_SCHEMA = "mart"
REF_SCHEMA = "ref"

#: mart.entity_* 契约列（与 ref.entity 一致）
ENTITY_COLUMNS: tuple[str, ...] = (
    "entity_id",
    "entity_type",
    "entity_class",
    "market",
    "code",
    "name",
    "currency",
    "exchange",
    "frequency",
    "unit",
    "algorithm_id",
    "social_status",
    "valid_from",
    "valid_to",
    "knowledge_time",
    "version",
)

_ENTITY_SELECT = ", ".join(ENTITY_COLUMNS)
#: 函数体内限定子查询列，避免与 RETURNS TABLE 输出参数同名歧义（PostgreSQL）
_ENTITY_SELECT_RANKED = ", ".join(f"ranked.{name}" for name in ENTITY_COLUMNS)


def entity_latest_view_sql(
    *,
    mart_schema: str = MART_SCHEMA,
    ref_schema: str = REF_SCHEMA,
    dialect: str = "postgresql",
) -> str:
    """当前态视图：``valid_to IS NULL`` 且同实体版本最高（读侧派生，不落列）。"""
    verb = "CREATE OR REPLACE VIEW" if dialect == "postgresql" else "CREATE VIEW"
    return (
        f"{verb} {mart_schema}.entity_latest_v1 AS\n"
        f"SELECT {_ENTITY_SELECT} FROM (\n"
        f"    SELECT {_ENTITY_SELECT},\n"
        "           ROW_NUMBER() OVER (\n"
        "               PARTITION BY entity_id\n"
        "               ORDER BY version DESC, knowledge_time DESC\n"
        "           ) AS _rank\n"
        f"    FROM {ref_schema}.entity\n"
        "    WHERE valid_to IS NULL\n"
        ") ranked\n"
        "WHERE _rank = 1;\n"
    )


def entity_asof_function_sql(
    *, mart_schema: str = MART_SCHEMA, ref_schema: str = REF_SCHEMA
) -> str:
    """属性 as-of 表函数（PostgreSQL；视图不可带参，doc-10 §3.3）。"""
    return (
        f"CREATE OR REPLACE FUNCTION {mart_schema}.entity_asof(as_of timestamptz)\n"
        "RETURNS TABLE (\n"
        "    entity_id bigint, entity_type text, entity_class text, market text,\n"
        "    code text, name text, currency text, exchange text, frequency text,\n"
        "    unit text, algorithm_id text, social_status text, valid_from date,\n"
        "    valid_to date, knowledge_time timestamptz, version bigint\n"
        ")\n"
        "LANGUAGE sql STABLE AS $$\n"
        f"    SELECT {_ENTITY_SELECT_RANKED}\n"
        "    FROM (\n"
        f"        SELECT e.{', e.'.join(ENTITY_COLUMNS)},\n"
        "               ROW_NUMBER() OVER (\n"
        "                   PARTITION BY e.entity_id\n"
        "                   ORDER BY e.version DESC, e.knowledge_time DESC\n"
        "               ) AS _rank\n"
        f"        FROM {ref_schema}.entity e\n"
        "        WHERE e.knowledge_time <= as_of\n"
        "          AND e.valid_from <= as_of::date\n"
        "          AND (e.valid_to IS NULL OR as_of::date <= e.valid_to)\n"
        "    ) ranked\n"
        "    WHERE _rank = 1;\n"
        "$$;\n"
    )


def entity_asof_query(as_of: datetime, *, table: Table = entity) -> Select[Any]:
    """跨方言 as-of 查询构造器：知识时间 <= as_of，属性区间覆盖 ``as_of::date``。"""
    valid = as_of.date()
    rank = (
        func.row_number()
        .over(
            partition_by=[table.c.entity_id],
            order_by=[table.c.version.desc(), table.c.knowledge_time.desc()],
        )
        .label("_rank")
    )
    statement = select(*table.c, rank).where(
        table.c.knowledge_time <= as_of,
        table.c.valid_from <= valid,
        (table.c.valid_to.is_(None)) | (valid <= table.c.valid_to),
    )
    subquery = statement.subquery()
    return select(*[subquery.c[column.name] for column in table.c]).where(
        subquery.c._rank == 1
    )


def entity_read_model_statements(*, dialect: str = "postgresql") -> list[str]:
    """读模型 DDL 清单（PG：视图 + 表函数；其他方言：仅视图）。"""
    statements = [entity_latest_view_sql(dialect=dialect)]
    if dialect == "postgresql":
        statements.append(entity_asof_function_sql())
    return statements


def ensure_entity_read_models(
    engine: Engine, *, mart_schema: str | None = None, ref_schema: str | None = None
) -> list[str]:
    """创建 schema/视图/函数（幂等；返回已执行语句）。

    PostgreSQL 默认 ``mart``/``ref`` schema；SQLite（本地/测试）默认 ``main``
    且仅支持视图（SQLite 视图不可跨 attached schema，函数不生成）。
    """
    is_sqlite = engine.dialect.name == "sqlite"
    mart = mart_schema or ("main" if is_sqlite else MART_SCHEMA)
    ref = ref_schema or ("main" if is_sqlite else REF_SCHEMA)
    statements = [
        entity_latest_view_sql(mart_schema=mart, ref_schema=ref, dialect=engine.dialect.name)
    ]
    if not is_sqlite:
        statements.append(entity_asof_function_sql(mart_schema=mart, ref_schema=ref))
    executed: list[str] = []
    with engine.begin() as connection:
        if not is_sqlite:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {mart}"))
            executed.append(f"CREATE SCHEMA IF NOT EXISTS {mart}")
        else:
            connection.execute(text(f"DROP VIEW IF EXISTS {mart}.entity_latest_v1"))
        for statement in statements:
            connection.execute(text(statement))
            executed.append(statement)
    return executed
