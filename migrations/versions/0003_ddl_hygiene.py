"""DDL 卫生（TASK-3.20）：canonical varchar→text；压缩键覆盖物理键。

由 :func:`ddl_hygiene_statements` 生成，请勿手改；
漂移校验：``tests/test_platform_migrations.py``。

Revision ID: 0003_ddl_hygiene
Revises: 0002_runtime_meta
"""

from __future__ import annotations

from alembic import op

revision = "0003_ddl_hygiene"
down_revision = "0002_runtime_meta"
branch_labels = None
depends_on = None


UPGRADE_STATEMENTS = [
    """DO $$
DECLARE rec record;
BEGIN
    FOR rec IN
        SELECT chunk_schema, chunk_name
        FROM timescaledb_information.chunks
        WHERE hypertable_schema IN ('cn_equity', 'cn_fund', 'ref') AND is_compressed
    LOOP
        CALL decompress_chunk(format('%I.%I', rec.chunk_schema, rec.chunk_name)::regclass, true);
    END LOOP;
END $$;""",
    """DROP VIEW IF EXISTS mart.entity_latest_v1;""",
    """DROP FUNCTION IF EXISTS mart.entity_asof(timestamptz);""",
    """DO $$
DECLARE rec record;
BEGIN
    FOR rec IN
        SELECT c.table_schema, c.table_name, c.column_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE t.table_type = 'BASE TABLE'
          AND c.data_type = 'character varying'
          AND c.table_schema IN ('cn_equity', 'cn_fund', 'ref')
    LOOP
        EXECUTE format('ALTER TABLE %I.%I ALTER COLUMN %I TYPE text',
                       rec.table_schema, rec.table_name, rec.column_name);
    END LOOP;
END $$;""",
    """CREATE OR REPLACE VIEW mart.entity_latest_v1 AS
SELECT entity_id, entity_type, entity_class, market, code, name, currency, exchange, frequency, unit, algorithm_id, social_status, valid_from, valid_to, knowledge_time, version FROM (
    SELECT entity_id, entity_type, entity_class, market, code, name, currency, exchange, frequency, unit, algorithm_id, social_status, valid_from, valid_to, knowledge_time, version,
           ROW_NUMBER() OVER (
               PARTITION BY entity_id
               ORDER BY version DESC, knowledge_time DESC
           ) AS _rank
    FROM ref.entity
    WHERE valid_to IS NULL
) ranked
WHERE _rank = 1;""",
    """CREATE OR REPLACE FUNCTION mart.entity_asof(as_of timestamptz)
RETURNS TABLE (
    entity_id bigint, entity_type text, entity_class text, market text,
    code text, name text, currency text, exchange text, frequency text,
    unit text, algorithm_id text, social_status text, valid_from date,
    valid_to date, knowledge_time timestamptz, version bigint
)
LANGUAGE sql STABLE AS $$
    SELECT ranked.entity_id, ranked.entity_type, ranked.entity_class, ranked.market, ranked.code, ranked.name, ranked.currency, ranked.exchange, ranked.frequency, ranked.unit, ranked.algorithm_id, ranked.social_status, ranked.valid_from, ranked.valid_to, ranked.knowledge_time, ranked.version
    FROM (
        SELECT e.entity_id, e.entity_type, e.entity_class, e.market, e.code, e.name, e.currency, e.exchange, e.frequency, e.unit, e.algorithm_id, e.social_status, e.valid_from, e.valid_to, e.knowledge_time, e.version,
               ROW_NUMBER() OVER (
                   PARTITION BY e.entity_id
                   ORDER BY e.version DESC, e.knowledge_time DESC
               ) AS _rank
        FROM ref.entity e
        WHERE e.knowledge_time <= as_of
          AND e.valid_from <= as_of::date
          AND (e.valid_to IS NULL OR as_of::date <= e.valid_to)
    ) ranked
    WHERE _rank = 1;
$$;""",
    """ALTER TABLE cn_equity.adj_factor SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'trade_date, knowledge_time, version');""",
    """ALTER TABLE cn_equity.daily_bar SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'trade_date, knowledge_time, version');""",
    """ALTER TABLE cn_equity.financials_balance_sheet SET (timescaledb.compress, timescaledb.compress_segmentby = 'issuer_id', timescaledb.compress_orderby = 'end_date, report_type, knowledge_time, version');""",
    """ALTER TABLE cn_equity.index_weight SET (timescaledb.compress, timescaledb.compress_segmentby = 'index_entity_id', timescaledb.compress_orderby = 'trade_date, con_entity_id, knowledge_time, version');""",
    """ALTER TABLE cn_fund.nav SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'date, knowledge_time, version');""",
]


DOWNGRADE_STATEMENTS = [
    """DO $$
DECLARE rec record;
BEGIN
    FOR rec IN
        SELECT chunk_schema, chunk_name
        FROM timescaledb_information.chunks
        WHERE hypertable_schema IN ('cn_equity', 'cn_fund', 'ref') AND is_compressed
    LOOP
        CALL decompress_chunk(format('%I.%I', rec.chunk_schema, rec.chunk_name)::regclass, true);
    END LOOP;
END $$;""",
    """DROP VIEW IF EXISTS mart.entity_latest_v1;""",
    """DROP FUNCTION IF EXISTS mart.entity_asof(timestamptz);""",
    """ALTER TABLE cn_equity.adj_factor SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'trade_date');""",
    """ALTER TABLE cn_equity.daily_bar SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'trade_date');""",
    """ALTER TABLE cn_equity.financials_balance_sheet SET (timescaledb.compress, timescaledb.compress_segmentby = 'issuer_id', timescaledb.compress_orderby = 'end_date');""",
    """ALTER TABLE cn_equity.index_weight SET (timescaledb.compress, timescaledb.compress_segmentby = 'index_entity_id', timescaledb.compress_orderby = 'trade_date');""",
    """ALTER TABLE cn_fund.nav SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'date');""",
    """CREATE OR REPLACE VIEW mart.entity_latest_v1 AS
SELECT entity_id, entity_type, entity_class, market, code, name, currency, exchange, frequency, unit, algorithm_id, social_status, valid_from, valid_to, knowledge_time, version FROM (
    SELECT entity_id, entity_type, entity_class, market, code, name, currency, exchange, frequency, unit, algorithm_id, social_status, valid_from, valid_to, knowledge_time, version,
           ROW_NUMBER() OVER (
               PARTITION BY entity_id
               ORDER BY version DESC, knowledge_time DESC
           ) AS _rank
    FROM ref.entity
    WHERE valid_to IS NULL
) ranked
WHERE _rank = 1;""",
    """CREATE OR REPLACE FUNCTION mart.entity_asof(as_of timestamptz)
RETURNS TABLE (
    entity_id bigint, entity_type text, entity_class text, market text,
    code text, name text, currency text, exchange text, frequency text,
    unit text, algorithm_id text, social_status text, valid_from date,
    valid_to date, knowledge_time timestamptz, version bigint
)
LANGUAGE sql STABLE AS $$
    SELECT ranked.entity_id, ranked.entity_type, ranked.entity_class, ranked.market, ranked.code, ranked.name, ranked.currency, ranked.exchange, ranked.frequency, ranked.unit, ranked.algorithm_id, ranked.social_status, ranked.valid_from, ranked.valid_to, ranked.knowledge_time, ranked.version
    FROM (
        SELECT e.entity_id, e.entity_type, e.entity_class, e.market, e.code, e.name, e.currency, e.exchange, e.frequency, e.unit, e.algorithm_id, e.social_status, e.valid_from, e.valid_to, e.knowledge_time, e.version,
               ROW_NUMBER() OVER (
                   PARTITION BY e.entity_id
                   ORDER BY e.version DESC, e.knowledge_time DESC
               ) AS _rank
        FROM ref.entity e
        WHERE e.knowledge_time <= as_of
          AND e.valid_from <= as_of::date
          AND (e.valid_to IS NULL OR as_of::date <= e.valid_to)
    ) ranked
    WHERE _rank = 1;
$$;""",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
