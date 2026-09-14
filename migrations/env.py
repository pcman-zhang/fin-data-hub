"""Alembic 运行环境：target_metadata 由数据字典生成（Schema First）。"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from fin_data_platform.storage.config import StorageConfig
from fin_data_platform.storage.engine import create_write_engine
from fin_data_platform.storage.schema import build_metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata, _specs = build_metadata()


def _database_url() -> str:
    """DSN 优先级：``-x db_url`` > ``alembic.ini``（程序化设置）> ``DATABASE_*`` 环境变量。"""
    x_args = context.get_x_argument(as_dictionary=True)
    if override := x_args.get("db_url"):
        return override
    if configured := config.get_main_option("sqlalchemy.url"):
        return configured
    return StorageConfig.from_env(
        host_override=os.environ.get("FDP_DATABASE_HOST")
    ).write_dsn


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_write_engine(
        StorageConfig(write_dsn=_database_url()), poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
