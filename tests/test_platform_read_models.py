"""读模型测试：``mart.entity_latest_v1`` / ``entity_asof``（SQLite 语义 + PG DDL 契约）。"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import MetaData, create_engine, insert, text
from sqlalchemy.pool import StaticPool

from fin_data_platform.registry.schema import entity
from fin_data_platform.storage import (
    entity_asof_function_sql,
    entity_asof_query,
    entity_latest_view_sql,
    entity_read_model_statements,
)


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as connection:
        for schema in ("ref", "mart"):
            connection.execute(text(f"ATTACH DATABASE ':memory:' AS {schema}"))
    entity.create(engine)
    return engine


def _rows() -> list[dict]:
    return [
        {
            "entity_id": 1,
            "entity_type": "equity",
            "code": "600519.SH",
            "name": "贵州茅台",
            "valid_from": date(1990, 1, 1),
            "valid_to": None,
            "knowledge_time": datetime(2026, 1, 1, 8),
            "version": 1,
        },
        {
            "entity_id": 1,
            "entity_type": "equity",
            "code": "600519.SH",
            "name": "茅台股份",
            "valid_from": date(1990, 1, 1),
            "valid_to": None,
            "knowledge_time": datetime(2026, 2, 1, 8),
            "version": 2,
        },
        {
            "entity_id": 2,
            "entity_type": "etf",
            "code": "510300.SH",
            "name": "300ETF",
            "valid_from": date(1990, 1, 1),
            "valid_to": date(2026, 1, 15),
            "knowledge_time": datetime(2026, 1, 1, 8),
            "version": 1,
        },
        {
            "entity_id": 2,
            "entity_type": "etf",
            "code": "510300.SH",
            "name": "300ETF",
            "valid_from": date(2026, 1, 16),
            "valid_to": None,
            "knowledge_time": datetime(2026, 1, 16, 8),
            "version": 2,
        },
    ]


def test_entity_latest_view_semantics(engine) -> None:
    # SQLite 视图不可跨 attached schema，故在 main 中建同名表与视图验证 SQL 语义
    local = entity.to_metadata(MetaData(), schema=None)
    local.create(engine)
    with engine.begin() as connection:
        connection.execute(insert(local), _rows())
        connection.execute(
            text(
                entity_latest_view_sql(
                    mart_schema="main", ref_schema="main", dialect="sqlite"
                )
            )
        )
        rows = connection.execute(
            text(
                "SELECT entity_id, name, version FROM main.entity_latest_v1 "
                "ORDER BY entity_id"
            )
        ).fetchall()
    assert [(row.entity_id, row.name, row.version) for row in rows] == [
        (1, "茅台股份", 2),
        (2, "300ETF", 2),
    ]


def test_entity_asof_query_knowledge_and_validity(engine) -> None:
    with engine.begin() as connection:
        connection.execute(insert(entity), _rows())
        early = connection.execute(entity_asof_query(datetime(2026, 1, 10, 12))).fetchall()
        assert {(row.entity_id, row.name, row.version) for row in early} == {
            (1, "贵州茅台", 1),
            (2, "300ETF", 1),
        }
        later = connection.execute(entity_asof_query(datetime(2026, 2, 1, 12))).fetchall()
        assert {(row.entity_id, row.name, row.version) for row in later} == {
            (1, "茅台股份", 2),
            (2, "300ETF", 2),
        }
        # 实体 2 的 v1 区间已关闭（2026-01-15），v2 知识时间未到（01-16 08:00 后可见）
        gap = connection.execute(entity_asof_query(datetime(2026, 1, 16, 7))).fetchall()
        assert {(row.entity_id, row.version) for row in gap} == {(1, 1)}


def test_entity_read_model_ddl_contract() -> None:
    view = entity_latest_view_sql()
    assert "CREATE OR REPLACE VIEW mart.entity_latest_v1" in view
    assert "PARTITION BY entity_id" in view
    assert "WHERE valid_to IS NULL" in view
    function = entity_asof_function_sql()
    assert "CREATE OR REPLACE FUNCTION mart.entity_asof(as_of timestamptz)" in function
    assert "RETURNS TABLE" in function
    assert "as_of::date" in function
    # 非 PG 方言仅生成视图
    assert entity_read_model_statements(dialect="sqlite") == [
        entity_latest_view_sql(dialect="sqlite")
    ]
