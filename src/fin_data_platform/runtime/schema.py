"""FinDataRuntime 控制面 schema（``meta.*``；doc-20 已定稿）。

表由迁移修订 0002 创建（基线 0001 不含 meta）；同时合并进
:func:`fin_data_platform.storage.schema.build_metadata` 供本地建库与文档生成。
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

#: doc-13 §1：控制面 schema
SCHEMA = "meta"

metadata = MetaData()

job_defs = Table(
    "job_defs",
    metadata,
    Column("job_id", String(64), primary_key=True),
    Column("kind", String(16), nullable=False),
    Column("dataset", String(64), nullable=False),
    Column("schedule", String(64)),
    Column("priority", Integer, nullable=False),
    Column("max_attempts", Integer, nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    schema=SCHEMA,
)

job_dependencies = Table(
    "job_dependencies",
    metadata,
    Column("parent_job", String(64), primary_key=True),
    Column("child_job", String(64), primary_key=True),
    Column("condition", String(16), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    schema=SCHEMA,
)
Index("ix_job_dependencies_child", job_dependencies.c.child_job)

job_runs = Table(
    "job_runs",
    metadata,
    Column("run_id", Integer, primary_key=True, autoincrement=True),
    Column("job_key", String(64), nullable=False),
    Column("job_id", String(64), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("dataset", String(64), nullable=False),
    Column("scope", String(64), nullable=False),
    Column("window_start", Date),
    Column("window_end", Date),
    Column("version_dimension", String(64)),
    Column("status", String(16), nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("max_attempts", Integer, nullable=False),
    Column("priority", Integer, nullable=False),
    Column("scheduled_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("rows_written", BigInteger),
    Column("error", Text),
    Column("request_id", String(64)),
    Column("worker", String(64)),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    schema=SCHEMA,
)
Index("ix_job_runs_job_key", job_runs.c.job_key)
Index("ix_job_runs_status", job_runs.c.status)

watermarks = Table(
    "watermarks",
    metadata,
    Column("dataset", String(64), primary_key=True),
    Column("scope", String(64), primary_key=True),
    Column("watermark_time", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    schema=SCHEMA,
)

TABLES = (job_defs, job_dependencies, job_runs, watermarks)
