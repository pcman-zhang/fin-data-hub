"""存储引擎工厂与 schema 初始化。"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.schema import CreateSchema, CreateTable

from fin_data_platform.storage.config import StorageConfig
from fin_data_platform.storage.schema import build_metadata, timescale_statements


def create_write_engine(config: StorageConfig, **kwargs: object) -> Engine:
    return create_engine(config.write_dsn, **kwargs)


def create_read_engine(config: StorageConfig, **kwargs: object) -> Engine:
    return create_engine(config.reader_dsn, **kwargs)


def ensure_schema(
    engine: Engine,
    *,
    config: StorageConfig | None = None,
    metadata=None,
    specs=None,
) -> list[str]:
    """创建 schema/表（幂等）；PostgreSQL + TimescaleDB 时追加 hypertable/压缩语句。

    返回已执行的语句列表（便于审查/迁移留档）。
    """
    if metadata is None:
        metadata, specs = build_metadata()
    elif specs is None:
        from fin_data_platform.dictionary import load_all

        specs = load_all()
    executed: list[str] = []
    schemas = sorted(
        {table.schema for table in metadata.tables.values() if table.schema}
    )
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as connection:
        if not is_sqlite:
            for schema in schemas:
                connection.execute(CreateSchema(schema, if_not_exists=True))
                executed.append(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        for table in metadata.sorted_tables:
            connection.execute(CreateTable(table, if_not_exists=True))
            executed.append(f"CREATE TABLE IF NOT EXISTS {table.key}")
        if (
            config is not None
            and config.timescale
            and not is_sqlite
            and engine.dialect.name == "postgresql"
            and specs
        ):
            for statement in timescale_statements(metadata, specs):
                connection.execute(text(statement))
                executed.append(statement)
    return executed
