"""迁移真实数据库集成测试（默认跳过：``pytest -m integration``）。

覆盖：upgrade → 校验表/hypertable → 重复 upgrade（幂等）→ downgrade base →
重复 downgrade（幂等）→ 再 upgrade。DSN 来源同 ``tests/test_integration_storage.py``。
"""

from __future__ import annotations

import os

import pytest
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from fin_data_platform.storage import StorageConfig
from fin_data_platform.storage.migrations import BASELINE_REVISION, downgrade, upgrade

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def dsn() -> str:
    if not os.environ.get("DATABASE_USER"):
        pytest.skip("缺少 DATABASE_* 环境变量")
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


def test_upgrade_downgrade_repeatable(dsn: str) -> None:
    downgrade(dsn, "base")  # 清理上次运行残留（无版本表时为 no-op）
    assert _current_revision(dsn) is None

    upgrade(dsn, "head")
    assert _current_revision(dsn) == BASELINE_REVISION
    assert _table_count(dsn, "cn_equity") >= 5
    assert _hypertable_count(dsn) >= 3

    upgrade(dsn, "head")  # 幂等：重复升级 no-op
    assert _current_revision(dsn) == BASELINE_REVISION

    downgrade(dsn, "base")
    assert _current_revision(dsn) is None
    assert _table_count(dsn, "cn_equity") == 0

    downgrade(dsn, "base")  # 幂等：重复回滚安全
    assert _current_revision(dsn) is None

    upgrade(dsn, "head")  # 回滚后可再次升级
    assert _current_revision(dsn) == BASELINE_REVISION
