"""Alembic 迁移的程序化入口（TASK-3.3.1，doc-13 §7）。

- 基线迁移由数据字典生成（Schema First）：:func:`baseline_statements` 产出冻结 DDL，
  :func:`render_baseline_script` 渲染修订文件；漂移校验见
  ``tests/test_platform_migrations.py``；
- :func:`upgrade` / :func:`downgrade` 供部署与集成测试调用（TASK-3.4 自动迁移）；
- DSN 由调用方或 ``DATABASE_*`` 环境变量提供（``FDP_DATABASE_HOST`` 可覆盖主机），
  凭证不落仓库。
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from fin_data_platform.storage.config import StorageConfig
from fin_data_platform.storage.read_models import (
    MART_SCHEMA,
    entity_read_model_drop_statements,
    entity_read_model_statements,
)
from fin_data_platform.storage.schema import (
    build_metadata,
    schema_sql,
    timescale_statements,
)

#: 仓库根（src/fin_data_platform/storage/migrations.py → 上溯 3 层）
REPO_ROOT = Path(__file__).resolve().parents[3]

BASELINE_REVISION = "0001_baseline"
BASELINE_PATH = REPO_ROOT / "migrations" / "versions" / f"{BASELINE_REVISION}.py"


def baseline_statements() -> tuple[list[str], list[str]]:
    """返回基线 ``(upgrade, downgrade)`` DDL 清单（由当前数据字典与读模型生成）。"""
    metadata, specs = build_metadata()
    upgrade = [
        f"CREATE SCHEMA IF NOT EXISTS {MART_SCHEMA}",
        *schema_sql(metadata, dialect="postgresql", if_not_exists=True),
        *timescale_statements(metadata, specs),
        *entity_read_model_statements(),
    ]
    downgrade = [
        *entity_read_model_drop_statements(),
        *(
            f"DROP TABLE IF EXISTS {table.key};"
            for table in reversed(metadata.sorted_tables)
        ),
    ]
    return upgrade, downgrade


def _statement_literals(statements: list[str]) -> list[str]:
    rendered: list[str] = []
    for statement in statements:
        text = statement.strip()
        if '"""' in text or text.endswith(('"', "\\")):
            rendered.append(f"    {text!r},")
        else:
            rendered.append(f'    """{text}""",')
    return rendered


def render_baseline_script() -> str:
    """渲染基线修订文件源码（冻结 DDL；字典变更后重新生成基线或新增修订）。"""
    upgrade, downgrade = baseline_statements()
    lines = [
        '"""基线迁移：由数据字典生成（Schema First；请勿手改）。',
        "",
        "生成来源：``fin_data_platform.storage.schema``（dictionary → metadata）；",
        "重新生成：``write_baseline()``；漂移校验：``tests/test_platform_migrations.py``。",
        "",
        "Revision ID: 0001_baseline",
        "Revises:",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from alembic import op",
        "",
        'revision = "0001_baseline"',
        "down_revision = None",
        "branch_labels = None",
        "depends_on = None",
        "",
        "",
        "UPGRADE_STATEMENTS = [",
        *_statement_literals(upgrade),
        "]",
        "",
        "",
        "DOWNGRADE_STATEMENTS = [",
        *_statement_literals(downgrade),
        "]",
        "",
        "",
        "def upgrade() -> None:",
        "    for statement in UPGRADE_STATEMENTS:",
        "        op.execute(statement)",
        "",
        "",
        "def downgrade() -> None:",
        "    for statement in DOWNGRADE_STATEMENTS:",
        "        op.execute(statement)",
        "",
    ]
    return "\n".join(lines)


def write_baseline(path: Path | None = None) -> Path:
    """写入/刷新基线修订文件（开发者操作；CI 校验生成结果与文件一致）。"""
    target = path or BASELINE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_baseline_script(), encoding="utf-8")
    return target


def _resolve_dsn(dsn: str | None) -> str:
    if dsn:
        return dsn
    return StorageConfig.from_env(
        host_override=os.environ.get("FDP_DATABASE_HOST")
    ).write_dsn


def alembic_config(dsn: str | None = None) -> Config:
    """构建 Alembic 配置（仓库内 ``alembic.ini`` + ``migrations/``）。"""
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    # configparser 插值：DSN 中的 % 需转义
    config.set_main_option("sqlalchemy.url", _resolve_dsn(dsn).replace("%", "%%"))
    return config


def upgrade(dsn: str | None = None, revision: str = "head") -> None:
    """升级到指定修订（默认 head）；重复执行幂等。"""
    command.upgrade(alembic_config(dsn), revision)


def downgrade(dsn: str | None = None, revision: str = "base") -> None:
    """回滚到指定修订（默认 base）；重复执行幂等。"""
    command.downgrade(alembic_config(dsn), revision)
