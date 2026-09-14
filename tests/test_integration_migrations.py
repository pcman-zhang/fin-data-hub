"""迁移真实数据库集成测试（默认跳过：``pytest -m integration``）。

覆盖：upgrade → 校验表/索引/hypertable → 重复 upgrade（幂等）→ downgrade base →
重复 downgrade（幂等）→ 再 upgrade。DSN 来源同 ``tests/test_integration_storage.py``。

警告：本测试会 **DROP 目标库的全部项目表与读模型**（downgrade base）。
需显式开启 ``FDP_TEST_DATABASE=1``，且必须确认 ``DATABASE_*`` 指向本地 dev 库
（``cp .env.example .env`` 后 source）。
"""

from __future__ import annotations

import os

import pytest
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from fin_data_platform.storage import StorageConfig
from fin_data_platform.storage.migrations import (
    downgrade,
    expected_head_revision,
    upgrade,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def dsn() -> str:
    if not os.environ.get("DATABASE_USER"):
        pytest.skip("缺少 DATABASE_* 环境变量")
    if os.environ.get("FDP_TEST_DATABASE") != "1":
        pytest.skip("破坏性迁移测试需显式开启：FDP_TEST_DATABASE=1（会清空目标库表结构）")
    return StorageConfig.from_env(
        host_override=os.environ.get("FDP_DATABASE_HOST")
    ).write_dsn


def _current_revision(dsn: str) -> str | None:
    engine = create_engine(dsn)
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()


def _table_count(dsn: str, schema: str) -> int:
    engine = create_engine(dsn)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text(
                    "select count(*) from information_schema.tables "
                    "where table_schema = :schema"
                ),
                {"schema": schema},
            ).scalar_one()
    finally:
        engine.dispose()


def _hypertable_count(dsn: str) -> int:
    engine = create_engine(dsn)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text("select count(*) from timescaledb_information.hypertables")
            ).scalar_one()
    finally:
        engine.dispose()


def _index_count(dsn: str, schema: str) -> int:
    engine = create_engine(dsn)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text(
                    "select count(*) from pg_indexes where schemaname = :schema"
                ),
                {"schema": schema},
            ).scalar_one()
    finally:
        engine.dispose()


def test_upgrade_downgrade_repeatable(dsn: str) -> None:
    downgrade(dsn, "base")  # 清理上次运行残留（无版本表时为 no-op）
    assert _current_revision(dsn) is None

    head = expected_head_revision(dsn)
    upgrade(dsn, "head")
    assert _current_revision(dsn) == head
    assert _table_count(dsn, "cn_equity") >= 5
    assert _table_count(dsn, "meta") >= 4  # 修订 0002：Runtime 控制面
    assert _hypertable_count(dsn) >= 3
    # doc-13 §4：业务索引随基线落地（ref 四索引 + cn_equity business 索引）
    assert _index_count(dsn, "ref") >= 4
    assert _index_count(dsn, "cn_equity") >= 5

    upgrade(dsn, "head")  # 幂等：重复升级 no-op
    assert _current_revision(dsn) == head

    downgrade(dsn, "base")
    assert _current_revision(dsn) is None
    assert _table_count(dsn, "cn_equity") == 0

    downgrade(dsn, "base")  # 幂等：重复回滚安全
    assert _current_revision(dsn) is None

    upgrade(dsn, "head")  # 回滚后可再次升级
    assert _current_revision(dsn) == head
