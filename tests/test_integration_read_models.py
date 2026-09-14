"""实体注册表读模型真实 PG 集成测试（默认跳过：``pytest -m integration``）。

验证 ``mart.entity_latest_v1`` 视图与 ``mart.entity_asof(ts)`` 表函数可在真实
PostgreSQL 创建并返回正确结果（RETURNS TABLE 列引用无歧义）。
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import Engine, create_engine, text

from fin_data_platform.storage import StorageConfig, ensure_entity_read_models
from fin_data_platform.storage.migrations import upgrade

pytestmark = pytest.mark.integration

_TEST_ENTITY = 999998


@pytest.fixture(scope="module")
def engine() -> Engine:
    if not os.environ.get("DATABASE_USER"):
        pytest.skip("缺少 DATABASE_* 环境变量")
    dsn = StorageConfig.from_env(
        host_override=os.environ.get("FDP_DATABASE_HOST")
    ).write_dsn
    upgrade(dsn, "head")  # 基线迁移（幂等）
    engine = create_engine(dsn)
    yield engine
    with engine.begin() as connection:
        connection.execute(
            text("delete from ref.entity where entity_id = :id"),
            {"id": _TEST_ENTITY},
        )
    engine.dispose()


def test_entity_read_models_run_on_postgres(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("delete from ref.entity where entity_id = :id"),
            {"id": _TEST_ENTITY},
        )
        connection.execute(
            text(
                "insert into ref.entity (entity_id, entity_type, code, name, "
                "valid_from, valid_to, knowledge_time, version) values "
                "(:id, 'equity', '600000.SH', '浦发银行', '1990-01-01', null, now(), 1)"
            ),
            {"id": _TEST_ENTITY},
        )
    ensure_entity_read_models(engine)
    with engine.begin() as connection:
        latest = connection.execute(
            text(
                "select entity_id, name from mart.entity_latest_v1 "
                "where entity_id = :id"
            ),
            {"id": _TEST_ENTITY},
        ).fetchall()
        asof = connection.execute(
            text(
                "select entity_id, name from mart.entity_asof(now()) "
                "where entity_id = :id"
            ),
            {"id": _TEST_ENTITY},
        ).fetchall()
    assert [tuple(row) for row in latest] == [(_TEST_ENTITY, "浦发银行")]
    assert [tuple(row) for row in asof] == [(_TEST_ENTITY, "浦发银行")]
