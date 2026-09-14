"""迁移（TASK-3.3.1）单元测试：基线 DDL 与字典一致（漂移校验）与回滚完备。"""

from __future__ import annotations

from fin_data_platform.storage.migrations import (
    BASELINE_PATH,
    alembic_config,
    baseline_statements,
    render_baseline_script,
)
from fin_data_platform.storage.schema import build_metadata


def test_baseline_script_matches_dictionary() -> None:
    """字典 → 迁移漂移校验：字典变更后必须重新生成基线（write_baseline）。"""
    assert BASELINE_PATH.read_text(encoding="utf-8") == render_baseline_script()


def test_baseline_upgrade_covers_schemas_tables_hypertables_and_read_models() -> None:
    upgrade, _ = baseline_statements()
    joined = "\n".join(upgrade)
    assert "CREATE SCHEMA IF NOT EXISTS cn_equity" in joined
    assert "CREATE SCHEMA IF NOT EXISTS mart" in joined
    assert "CREATE TABLE IF NOT EXISTS cn_equity.daily_bar" in joined
    assert (
        "create_hypertable('cn_equity.financials_balance_sheet', 'knowledge_time'"
        in joined
    )
    assert "add_compression_policy('cn_equity.daily_bar'" in joined
    # doc-13 §4：默认不建物理外键；读模型（mart.entity_*）纳入基线
    assert "REFERENCES" not in joined
    assert "CREATE OR REPLACE VIEW mart.entity_latest_v1" in joined
    assert "CREATE OR REPLACE FUNCTION mart.entity_asof(as_of timestamptz)" in joined


def test_baseline_downgrade_drops_read_models_then_tables() -> None:
    metadata, _ = build_metadata()
    _, downgrade = baseline_statements()
    # 先删依赖 ref.entity 的读模型，再删基表（否则 DROP TABLE 被依赖阻塞）
    assert downgrade[:2] == [
        "DROP VIEW IF EXISTS mart.entity_latest_v1;",
        "DROP FUNCTION IF EXISTS mart.entity_asof(timestamptz);",
    ]
    table_drops = [statement for statement in downgrade if statement.startswith("DROP TABLE")]
    assert len(table_drops) == len(metadata.tables)
    dropped = {
        statement.removeprefix("DROP TABLE IF EXISTS ").removesuffix(";")
        for statement in table_drops
    }
    assert dropped == set(metadata.tables)


def test_alembic_config_escapes_dsn_interpolation() -> None:
    config = alembic_config("postgresql+psycopg://u:p%40w@localhost:5432/db")
    assert config.get_main_option("script_location").endswith("migrations")
    # configparser 插值后还原原始密码（% 转义）
    assert config.get_main_option("sqlalchemy.url").endswith("p%40w@localhost:5432/db")
