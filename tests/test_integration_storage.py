"""存储层真实数据库集成测试（默认跳过：``pytest -m integration``）。

依赖环境变量 ``DATABASE_HOST/PORT/USER/PASSWORD``（``DATABASE_NAME`` 可选，
默认 ``fin_data_platform``）；DHCP 场景可用 ``FDP_DATABASE_HOST`` 覆盖主机。
"""

from __future__ import annotations

import os
from datetime import date, datetime

import pytest
from sqlalchemy import delete, func, select, text

from fin_data_platform.storage import (
    StorageConfig,
    append_rows,
    as_of_query,
    build_metadata,
    create_write_engine,
    ensure_schema,
    latest_query,
)

pytestmark = pytest.mark.integration

_TEST_ENTITY = 999999


@pytest.fixture(scope="module")
def engine():
    if not os.environ.get("DATABASE_USER"):
        pytest.skip("缺少 DATABASE_* 环境变量")
    config = StorageConfig.from_env(
        host_override=os.environ.get("FDP_DATABASE_HOST")
    )
    engine = create_write_engine(config)
    metadata, specs = build_metadata()
    ensure_schema(engine, config=config, metadata=metadata, specs=specs)
    yield engine, metadata
    table = metadata.tables["cn_equity.daily_bar"]
    with engine.begin() as connection:
        connection.execute(delete(table).where(table.c.entity_id == _TEST_ENTITY))
    engine.dispose()


def _row(version: int, close: float, knowledge: datetime) -> dict:
    return {
        "entity_id": _TEST_ENTITY,
        "trade_date": date(2026, 1, 5),
        "close": close,
        "knowledge_time": knowledge,
        "ingest_time": knowledge,
        "version": version,
        "provider": "tushare",
    }


def test_schema_idempotent_and_hypertable(engine) -> None:
    db, metadata = engine
    with db.connect() as connection:
        hyper = connection.execute(
            text(
                "select count(*) from timescaledb_information.hypertables "
                "where hypertable_name = 'daily_bar'"
            )
        ).scalar_one()
    assert hyper == 1
    # 二次 ensure_schema 不报错（幂等）
    config = StorageConfig(write_dsn=str(db.url.render_as_string(hide_password=False)))
    ensure_schema(db, config=config, metadata=metadata)


def test_idempotent_append_and_as_of(engine) -> None:
    db, metadata = engine
    table = metadata.tables["cn_equity.daily_bar"]
    rows = [
        _row(1, 10.0, datetime(2026, 1, 5, 18, 0)),
        _row(2, 12.0, datetime(2026, 2, 1, 18, 0)),
    ]
    with db.begin() as connection:
        connection.execute(delete(table).where(table.c.entity_id == _TEST_ENTITY))
        first = append_rows(connection, table, rows)
        second = append_rows(connection, table, rows)
        total = connection.execute(
            select(func.count())
            .select_from(table)
            .where(table.c.entity_id == _TEST_ENTITY)
        ).scalar_one()
        early = connection.execute(
            as_of_query(
                table,
                as_of=datetime(2026, 1, 15),
                key_columns=["entity_id", "trade_date"],
                filters=[table.c.entity_id == _TEST_ENTITY],
            )
        ).mappings().all()
        latest = connection.execute(
            latest_query(
                table,
                key_columns=["entity_id", "trade_date"],
                filters=[table.c.entity_id == _TEST_ENTITY],
            )
        ).mappings().all()
    assert first == 2
    assert second == 0
    assert total == 2
    assert float(early[0]["close"]) == 10.0
    assert float(latest[0]["close"]) == 12.0
