"""存储层：schema 生成、引擎、幂等写入与 PIT 读取（doc-13）。"""

from fin_data_platform.storage.config import StorageConfig
from fin_data_platform.storage.engine import (
    create_read_engine,
    create_write_engine,
    ensure_schema,
)
from fin_data_platform.storage.read_models import (
    ensure_entity_read_models,
    entity_asof_function_sql,
    entity_asof_query,
    entity_latest_view_sql,
    entity_read_model_drop_statements,
    entity_read_model_statements,
)
from fin_data_platform.storage.readers import as_of_query, latest_query
from fin_data_platform.storage.schema import (
    build_metadata,
    column_type,
    schema_sql,
    timescale_statements,
)
from fin_data_platform.storage.writers import append_rows

__all__ = [
    "StorageConfig",
    "append_rows",
    "as_of_query",
    "build_metadata",
    "column_type",
    "create_read_engine",
    "create_write_engine",
    "ensure_entity_read_models",
    "ensure_schema",
    "entity_asof_function_sql",
    "entity_asof_query",
    "entity_latest_view_sql",
    "entity_read_model_drop_statements",
    "entity_read_model_statements",
    "latest_query",
    "schema_sql",
    "timescale_statements",
]
