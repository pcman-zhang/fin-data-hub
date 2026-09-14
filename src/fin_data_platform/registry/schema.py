"""引用注册表存储 schema（SQLAlchemy Core 元数据）。

DDL 生成与迁移执行由 TASK-3.3 接入；本模块提供可复用的表定义。
表结构以数据字典（Schema First）为准，本模块为字典条目的存储镜像。
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
    Column("entity_class", String(32)),
    Column("market", String(16)),
    Column("code", String(32), nullable=False),
    Column("name", String(64), nullable=False),
    Column("currency", String(8)),
    Column("exchange", String(16)),
    Column("frequency", String(16)),
    Column("unit", String(16)),
    Column("algorithm_id", String(64)),
    Column("social_status", String(16)),
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

entity_relation = Table(
    "entity_relation",
    metadata,
    Column("entity_id", BigInteger, primary_key=True),
    Column("related_id", BigInteger, primary_key=True),
    Column("relation_type", String(32), primary_key=True),
    Column("valid_from", Date, primary_key=True),
    Column("valid_to", Date),
    Column("knowledge_time", DateTime(timezone=True), primary_key=True),
    Column("version", BigInteger, primary_key=True),
    schema=SCHEMA,
)
Index("ix_entity_relation_related", entity_relation.c.related_id)

entity_external_id = Table(
    "entity_external_id",
    metadata,
    Column("entity_id", BigInteger, primary_key=True),
    Column("id_type", String(16), primary_key=True),
    Column("id_value", String(64), primary_key=True),
    Column("valid_from", Date, primary_key=True),
    Column("valid_to", Date),
    Column("knowledge_time", DateTime(timezone=True), primary_key=True),
    Column("version", BigInteger, primary_key=True),
    schema=SCHEMA,
)
Index("ix_entity_external_id_value", entity_external_id.c.id_value)

relation_type_dict = Table(
    "relation_type_dict",
    metadata,
    Column("relation_type", String(32), primary_key=True),
    Column("inverse_relation", String(32), nullable=False),
    Column("description", String(128), nullable=False),
    schema=SCHEMA,
)

TABLES = (
    entity,
    entity_code_history,
    entity_relation,
    entity_external_id,
    relation_type_dict,
)
