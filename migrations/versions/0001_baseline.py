"""基线迁移：由数据字典生成（Schema First；请勿手改）。

生成来源：``fin_data_platform.storage.schema``（dictionary → metadata）；
重新生成：``write_baseline()``；漂移校验：``tests/test_platform_migrations.py``。

Revision ID: 0001_baseline
Revises:
"""

from __future__ import annotations

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


UPGRADE_STATEMENTS = [
    """CREATE SCHEMA IF NOT EXISTS mart""",
    """CREATE SCHEMA IF NOT EXISTS cn_equity""",
    """CREATE SCHEMA IF NOT EXISTS cn_fund""",
    """CREATE SCHEMA IF NOT EXISTS ref""",
    """CREATE TABLE IF NOT EXISTS cn_equity.adj_factor (
	entity_id BIGINT NOT NULL, 
	trade_date DATE NOT NULL, 
	adj_factor NUMERIC(20, 6) NOT NULL, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	ingest_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	provider TEXT NOT NULL, 
	PRIMARY KEY (entity_id, trade_date, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_adj_factor_business ON cn_equity.adj_factor (entity_id, trade_date)""",
    """CREATE TABLE IF NOT EXISTS cn_equity.daily_bar (
	entity_id BIGINT NOT NULL, 
	trade_date DATE NOT NULL, 
	open DOUBLE PRECISION, 
	high DOUBLE PRECISION, 
	low DOUBLE PRECISION, 
	close DOUBLE PRECISION, 
	volume DOUBLE PRECISION, 
	amount NUMERIC(24, 4), 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	publish_time TIMESTAMP WITH TIME ZONE, 
	ingest_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	provider TEXT NOT NULL, 
	PRIMARY KEY (entity_id, trade_date, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_daily_bar_business ON cn_equity.daily_bar (entity_id, trade_date)""",
    """CREATE TABLE IF NOT EXISTS cn_equity.financials_balance_sheet (
	issuer_id BIGINT NOT NULL, 
	ann_date DATE NOT NULL, 
	end_date DATE NOT NULL, 
	report_type TEXT NOT NULL, 
	total_assets NUMERIC(24, 4), 
	total_liab NUMERIC(24, 4), 
	total_cur_assets NUMERIC(24, 4), 
	total_cur_liab NUMERIC(24, 4), 
	money_cap NUMERIC(24, 4), 
	inventories NUMERIC(24, 4), 
	fix_assets NUMERIC(24, 4), 
	goodwill NUMERIC(24, 4), 
	total_hldr_eqy_exc_min_int NUMERIC(24, 4), 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	ingest_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	provider TEXT NOT NULL, 
	PRIMARY KEY (issuer_id, end_date, report_type, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_financials_balance_sheet_business ON cn_equity.financials_balance_sheet (issuer_id, end_date, report_type)""",
    """CREATE TABLE IF NOT EXISTS cn_equity.index_member (
	entity_id BIGINT NOT NULL, 
	l1_code TEXT NOT NULL, 
	l1_name TEXT NOT NULL, 
	l2_code TEXT NOT NULL, 
	l2_name TEXT NOT NULL, 
	l3_code TEXT NOT NULL, 
	l3_name TEXT NOT NULL, 
	in_date DATE NOT NULL, 
	out_date DATE, 
	is_new BOOLEAN NOT NULL, 
	PRIMARY KEY (entity_id, l3_code, in_date)
)""",
    """CREATE INDEX IF NOT EXISTS ix_index_member_business ON cn_equity.index_member (entity_id, l3_code, in_date)""",
    """CREATE TABLE IF NOT EXISTS cn_equity.index_weight (
	index_entity_id BIGINT NOT NULL, 
	trade_date DATE NOT NULL, 
	con_entity_id BIGINT NOT NULL, 
	weight NUMERIC(12, 6) NOT NULL, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	ingest_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	provider TEXT NOT NULL, 
	PRIMARY KEY (index_entity_id, trade_date, con_entity_id, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_index_weight_business ON cn_equity.index_weight (index_entity_id, trade_date, con_entity_id)""",
    """CREATE TABLE IF NOT EXISTS cn_equity.listing_lifecycle (
	entity_id BIGINT NOT NULL, 
	status TEXT NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE, 
	reason TEXT, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	provider TEXT NOT NULL, 
	PRIMARY KEY (entity_id, start_date, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_listing_lifecycle_business ON cn_equity.listing_lifecycle (entity_id, start_date)""",
    """CREATE TABLE IF NOT EXISTS cn_equity.market_events_namechange (
	entity_id BIGINT NOT NULL, 
	name TEXT NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE, 
	ann_date DATE, 
	change_reason TEXT, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	provider TEXT NOT NULL, 
	PRIMARY KEY (entity_id, start_date, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_market_events_namechange_business ON cn_equity.market_events_namechange (entity_id, start_date)""",
    """CREATE TABLE IF NOT EXISTS cn_fund.nav (
	entity_id BIGINT NOT NULL, 
	date DATE NOT NULL, 
	unit_nav NUMERIC(16, 6) NOT NULL, 
	accum_nav NUMERIC(16, 6), 
	daily_return DOUBLE PRECISION, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	ingest_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	provider TEXT NOT NULL, 
	PRIMARY KEY (entity_id, date, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_nav_business ON cn_fund.nav (entity_id, date)""",
    """CREATE TABLE IF NOT EXISTS ref.entity (
	entity_id BIGINT NOT NULL, 
	entity_type TEXT NOT NULL, 
	entity_class TEXT, 
	market TEXT, 
	code TEXT NOT NULL, 
	name TEXT NOT NULL, 
	currency TEXT, 
	exchange TEXT, 
	frequency TEXT, 
	unit TEXT, 
	algorithm_id TEXT, 
	social_status TEXT, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	PRIMARY KEY (entity_id, valid_from, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_entity_business ON ref.entity (entity_id, valid_from)""",
    """CREATE INDEX IF NOT EXISTS ix_entity_code ON ref.entity (code)""",
    """CREATE TABLE IF NOT EXISTS ref.entity_code_history (
	entity_id BIGINT NOT NULL, 
	code TEXT NOT NULL, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	PRIMARY KEY (entity_id, code, valid_from, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_entity_code_history_business ON ref.entity_code_history (entity_id, code, valid_from)""",
    """CREATE INDEX IF NOT EXISTS ix_entity_code_history_code ON ref.entity_code_history (code)""",
    """CREATE TABLE IF NOT EXISTS ref.entity_external_id (
	entity_id BIGINT NOT NULL, 
	id_type TEXT NOT NULL, 
	id_value TEXT NOT NULL, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	PRIMARY KEY (entity_id, id_type, id_value, valid_from, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_entity_external_id_business ON ref.entity_external_id (entity_id, id_type, id_value, valid_from)""",
    """CREATE INDEX IF NOT EXISTS ix_entity_external_id_value ON ref.entity_external_id (id_value)""",
    """CREATE TABLE IF NOT EXISTS ref.entity_relation (
	entity_id BIGINT NOT NULL, 
	related_id BIGINT NOT NULL, 
	relation_type TEXT NOT NULL, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	PRIMARY KEY (entity_id, related_id, relation_type, valid_from, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_entity_relation_business ON ref.entity_relation (entity_id, related_id, relation_type, valid_from)""",
    """CREATE INDEX IF NOT EXISTS ix_entity_relation_related ON ref.entity_relation (related_id)""",
    """CREATE TABLE IF NOT EXISTS ref.relation_type_dict (
	relation_type TEXT NOT NULL, 
	inverse_relation TEXT NOT NULL, 
	description TEXT NOT NULL, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	knowledge_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	version BIGINT NOT NULL, 
	PRIMARY KEY (relation_type, valid_from, knowledge_time, version)
)""",
    """CREATE INDEX IF NOT EXISTS ix_relation_type_dict_business ON ref.relation_type_dict (relation_type, valid_from)""",
    """SELECT create_hypertable('cn_equity.adj_factor', 'trade_date', chunk_time_interval => INTERVAL '1 month', migrate_data => TRUE, if_not_exists => TRUE);""",
    """ALTER TABLE cn_equity.adj_factor SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'trade_date, knowledge_time, version');""",
    """SELECT add_compression_policy('cn_equity.adj_factor', INTERVAL '7 days', if_not_exists => TRUE);""",
    """SELECT create_hypertable('cn_equity.daily_bar', 'trade_date', chunk_time_interval => INTERVAL '1 month', migrate_data => TRUE, if_not_exists => TRUE);""",
    """ALTER TABLE cn_equity.daily_bar SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'trade_date, knowledge_time, version');""",
    """SELECT add_compression_policy('cn_equity.daily_bar', INTERVAL '7 days', if_not_exists => TRUE);""",
    """SELECT create_hypertable('cn_equity.financials_balance_sheet', 'knowledge_time', chunk_time_interval => INTERVAL '6 months', migrate_data => TRUE, if_not_exists => TRUE);""",
    """ALTER TABLE cn_equity.financials_balance_sheet SET (timescaledb.compress, timescaledb.compress_segmentby = 'issuer_id', timescaledb.compress_orderby = 'end_date, report_type, knowledge_time, version');""",
    """SELECT add_compression_policy('cn_equity.financials_balance_sheet', INTERVAL '30 days', if_not_exists => TRUE);""",
    """SELECT create_hypertable('cn_equity.index_weight', 'trade_date', chunk_time_interval => INTERVAL '1 year', migrate_data => TRUE, if_not_exists => TRUE);""",
    """ALTER TABLE cn_equity.index_weight SET (timescaledb.compress, timescaledb.compress_segmentby = 'index_entity_id', timescaledb.compress_orderby = 'trade_date, con_entity_id, knowledge_time, version');""",
    """SELECT add_compression_policy('cn_equity.index_weight', INTERVAL '30 days', if_not_exists => TRUE);""",
    """SELECT create_hypertable('cn_fund.nav', 'date', chunk_time_interval => INTERVAL '1 year', migrate_data => TRUE, if_not_exists => TRUE);""",
    """ALTER TABLE cn_fund.nav SET (timescaledb.compress, timescaledb.compress_segmentby = 'entity_id', timescaledb.compress_orderby = 'date, knowledge_time, version');""",
    """SELECT add_compression_policy('cn_fund.nav', INTERVAL '7 days', if_not_exists => TRUE);""",
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


DOWNGRADE_STATEMENTS = [
    """DROP VIEW IF EXISTS mart.entity_latest_v1;""",
    """DROP FUNCTION IF EXISTS mart.entity_asof(timestamptz);""",
    """DROP TABLE IF EXISTS ref.relation_type_dict;""",
    """DROP TABLE IF EXISTS ref.entity_relation;""",
    """DROP TABLE IF EXISTS ref.entity_external_id;""",
    """DROP TABLE IF EXISTS ref.entity_code_history;""",
    """DROP TABLE IF EXISTS ref.entity;""",
    """DROP TABLE IF EXISTS cn_fund.nav;""",
    """DROP TABLE IF EXISTS cn_equity.market_events_namechange;""",
    """DROP TABLE IF EXISTS cn_equity.listing_lifecycle;""",
    """DROP TABLE IF EXISTS cn_equity.index_weight;""",
    """DROP TABLE IF EXISTS cn_equity.index_member;""",
    """DROP TABLE IF EXISTS cn_equity.financials_balance_sheet;""",
    """DROP TABLE IF EXISTS cn_equity.daily_bar;""",
    """DROP TABLE IF EXISTS cn_equity.adj_factor;""",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
