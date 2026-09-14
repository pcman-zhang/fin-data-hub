"""Runtime 控制面 schema（meta.*；doc-20）。由 runtime/schema.py 生成，请勿手改。

重新生成：``write_runtime_meta_revision()``；漂移校验：``tests/test_platform_migrations.py``。

Revision ID: 0002_runtime_meta
Revises: 0001_baseline
"""

from __future__ import annotations

from alembic import op

revision = "0002_runtime_meta"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


UPGRADE_STATEMENTS = [
    """CREATE SCHEMA IF NOT EXISTS meta""",
    """CREATE TABLE IF NOT EXISTS meta.job_defs (
	job_id VARCHAR(64) NOT NULL, 
	kind VARCHAR(16) NOT NULL, 
	dataset VARCHAR(64) NOT NULL, 
	schedule VARCHAR(64), 
	priority INTEGER NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (job_id)
)""",
    """CREATE TABLE IF NOT EXISTS meta.job_dependencies (
	parent_job VARCHAR(64) NOT NULL, 
	child_job VARCHAR(64) NOT NULL, 
	condition VARCHAR(16) NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (parent_job, child_job)
)""",
    """CREATE INDEX IF NOT EXISTS ix_job_dependencies_child ON meta.job_dependencies (child_job)""",
    """CREATE TABLE IF NOT EXISTS meta.job_runs (
	run_id SERIAL NOT NULL, 
	job_key VARCHAR(64) NOT NULL, 
	job_id VARCHAR(64) NOT NULL, 
	kind VARCHAR(16) NOT NULL, 
	dataset VARCHAR(64) NOT NULL, 
	scope VARCHAR(64) NOT NULL, 
	window_start DATE, 
	window_end DATE, 
	version_dimension VARCHAR(64), 
	status VARCHAR(16) NOT NULL, 
	attempt INTEGER NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	priority INTEGER NOT NULL, 
	scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	rows_written BIGINT, 
	error TEXT, 
	request_id VARCHAR(64), 
	worker VARCHAR(64), 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (run_id)
)""",
    """CREATE INDEX IF NOT EXISTS ix_job_runs_job_key ON meta.job_runs (job_key)""",
    """CREATE INDEX IF NOT EXISTS ix_job_runs_status ON meta.job_runs (status)""",
    """CREATE TABLE IF NOT EXISTS meta.watermarks (
	dataset VARCHAR(64) NOT NULL, 
	scope VARCHAR(64) NOT NULL, 
	watermark_time TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (dataset, scope)
)""",
]


DOWNGRADE_STATEMENTS = [
    """DROP TABLE IF EXISTS meta.watermarks;""",
    """DROP TABLE IF EXISTS meta.job_runs;""",
    """DROP TABLE IF EXISTS meta.job_dependencies;""",
    """DROP TABLE IF EXISTS meta.job_defs;""",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
