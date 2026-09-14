"""引用注册表存储 schema（SQLAlchemy Core 元数据）。

DDL 生成与迁移执行由 TASK-3.3 接入；本模块提供可复用的表定义。
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Index,
    MetaData,
    String,
    Table,
)

#: doc-13 §1：参照数据 schema
SCHEMA = "ref"

metadata = MetaData()

entity = Table(
    "entity",
    metadata,
    Column("entity_id", BigInteger, primary_key=True),
    Column("entity_type", String(16), nullable=False),
    Column("code", String(32), nullable=False),
    Column("name", String(64), nullable=False),
    Column("status", String(16), nullable=False),
    Column("sec_type", String(16)),
    Column("currency", String(8)),
    Column("exchange", String(16)),
    Column("frequency", String(16)),
    Column("unit", String(16)),
    Column("list_date", Date),
    Column("delist_date", Date),
    Column("algorithm_id", String(64)),
    Column("valid_from", Date, primary_key=True),
    Column("valid_to", Date),
    Column("knowledge_time", DateTime(timezone=True), primary_key=True),
    Column("version", BigInteger, primary_key=True),
    schema=SCHEMA,
)
Index("ix_entity_code", entity.c.code)

entity_code_history = Table(
    "entity_code_history",
    metadata,
    Column("entity_id", BigInteger, primary_key=True),
    Column("code", String(32), primary_key=True),
    Column("valid_from", Date, primary_key=True),
    Column("valid_to", Date),
    Column("knowledge_time", DateTime(timezone=True), primary_key=True),
    Column("version", BigInteger, primary_key=True),
    schema=SCHEMA,
)
Index("ix_entity_code_history_code", entity_code_history.c.code)

TABLES = (entity, entity_code_history)
