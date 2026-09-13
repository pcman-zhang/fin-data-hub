"""Security Master 存储 schema（SQLAlchemy Core 元数据）。

DDL 生成与迁移执行由 TASK-3.3（存储层）接入；本模块提供可复用的表定义。
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

security_master = Table(
    "security_master",
    metadata,
    Column("security_id", BigInteger, primary_key=True),
    Column("canonical_code", String(32), nullable=False),
    Column("sec_type", String(16), nullable=False),
    Column("name", String(64), nullable=False),
    Column("currency", String(8)),
    Column("list_date", Date),
    Column("delist_date", Date),
    Column("status", String(4), nullable=False),
    Column("valid_from", Date, primary_key=True),
    Column("valid_to", Date),
    Column("knowledge_time", DateTime(timezone=True), nullable=False),
    Column("version", BigInteger, nullable=False),
    schema=SCHEMA,
)
Index(
    "ux_security_master_canonical",
    security_master.c.canonical_code,
    security_master.c.valid_from,
    unique=True,
)

security_alias = Table(
    "security_alias",
    metadata,
    Column("security_id", BigInteger, primary_key=True),
    Column("source", String(16), primary_key=True),
    Column("source_code", String(32), primary_key=True),
    Column("valid_from", Date, primary_key=True),
    Column("valid_to", Date),
    Column("knowledge_time", DateTime(timezone=True), nullable=False),
    Column("version", BigInteger, nullable=False),
    schema=SCHEMA,
)
Index(
    "ix_security_alias_source_code",
    security_alias.c.source,
    security_alias.c.source_code,
)

security_status_history = Table(
    "security_status_history",
    metadata,
    Column("security_id", BigInteger, primary_key=True),
    Column("start_date", Date, primary_key=True),
    Column("status", String(4), nullable=False),
    Column("end_date", Date),
    Column("knowledge_time", DateTime(timezone=True), nullable=False),
    Column("version", BigInteger, nullable=False),
    schema=SCHEMA,
)

security_attribute_history = Table(
    "security_attribute_history",
    metadata,
    Column("security_id", BigInteger, primary_key=True),
    Column("attribute", String(32), primary_key=True),
    Column("start_date", Date, primary_key=True),
    Column("value", String(128), nullable=False),
    Column("end_date", Date),
    Column("ann_date", Date),
    Column("knowledge_time", DateTime(timezone=True), nullable=False),
    Column("version", BigInteger, nullable=False),
    schema=SCHEMA,
)

TABLES = (
    security_master,
    security_alias,
    security_status_history,
    security_attribute_history,
)
