---
id: TASK-3.3
title: TimescaleDB 存储层：schema / 分区 / 迁移 / 幂等增量
status: Done
assignee: []
created_date: '2026-09-13 05:59'
updated_date: '2026-09-14 06:35'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
parent_task_id: TASK-3
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
基于 PostgreSQL + TimescaleDB 落地存储：hypertable 与分区设计（按数据域/时间）、连续聚合与压缩/保留策略、迁移管理、幂等 upsert、增量同步与历史回填、PIT 双时间轴字段（事件时间+知识时间）；**只读角色与按域授权（供只读副本/SDK，禁止内部原始表）**；复用 v0 适配器与统一 schema。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 字典→SQLAlchemy schema（类型映射/物理键主键/业务索引/ref 表合并）+ Timescale hypertable/压缩语句生成
- [x] #2 幂等写入（ON CONFLICT + RETURNING 计数）+ as-of/latest 读取（含 filters）
- [x] #3 真实库集成验证（PG17 + TimescaleDB：hypertable/压缩策略/幂等/as-of）；集成测试（-m integration）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
第一期切片：① storage/config（读写 DSN 分离）；② storage/schema（字典→SQLAlchemy metadata + 类型映射 + hypertable/压缩 DDL 生成）；③ storage/engine（引擎工厂/ensure_schema/schema_sql）；④ storage/writers（幂等 append：PG/SQLite ON CONFLICT DO NOTHING）；⑤ storage/readers（as-of/latest 窗口查询）；⑥ SQLite 测试（schema/幂等/as-of）+ Timescale DDL 字符串断言。后续切片：Alembic 迁移、Parquet/CSV 导入、只读角色授权、性能验证。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
存储按 PIT 分级落地：append-only 版本表 + is_latest 物化视图；复权因子版本化、复权价读时按 as-of 计算；指数成分用生效区间 + SCD2（doc-2 §6.9）。

读写模块设计（2026-09-13，doc-2 §6.13）：storage/{engine,schema,migrations,writers,readers,versioning}；写入=staging+COPY→幂等 merge+PIT append-only+advisory lock+job_runs，提交后刷新 is_latest/连续聚合并递增 Redis 代际；读取=as-of（DISTINCT ON/window）+ 读模型视图 + 游标分页 + Arrow；选型 SQLAlchemy Core + Alembic + psycopg3；读写 DSN/角色分离。

修正（2026-09-13）：写入端不限于 scheduler——派生计算/文件导入/质量结果也是内部写入端；按 schema 最小授权（ingestion→raw/staging+主数据、derived→derived、import→raw、quality→quality）；派生管线见 TASK-3.12。

时序存储（2026-09-13）：hypertable 按 (panel,key,event_time) 分区；knowledge_time 版本维度；按频率连续聚合；time_bucket_gapfill；压缩/保留按频率分级（doc-2 §6.14）。

存储策略输入（2026-09-13，doc-13）：域 schema、hypertable 分区策略（按 pit_class 推导）、物理键唯一索引、不建 FK、is_latest 读侧派生、投影表代次 rename/swap、压缩参数登记字典。

DDL 输入约定（2026-09-13）：canonical_table = `<domain>.<其余路径以下划线连接>`（如 cn_equity.financials_balance_sheet）；read_model = mart.<name>_v<semantic_version>；partition_strategy 按 pit_class 默认推导。

消费项（2026-09-13）：Security Master 四表 schema 定义见 fin_data_platform.security_master.schema（ref schema，含唯一/查询索引）；DDL 生成与迁移执行由本任务接入；持久化仓储实现替换内存仓储（SecurityMasterRepository 协议）。

第一期切片完成（2026-09-13）：storage/{config,schema,engine,writers,readers}——字典→SQLAlchemy metadata（类型映射/物理键主键/业务索引/ref 表合并）；hypertable/压缩 DDL 生成（按 partition_strategy）；ensure_schema（幂等，SQLite 跳过 schema 语句）；幂等 append（PG/SQLite ON CONFLICT DO NOTHING）；as-of/latest 窗口查询（按 business_key 分组——修复物理键含 version 导致的错误分组）。测试 5 项（SQLite 语义 + PG DDL 字符串）。全量 308 passed；ruff/mypy clean。待办切片：Alembic 迁移/回滚（AC#2）、Parquet/CSV 幂等导入（AC#4）、只读角色授权、PG/Timescale 集成验证与性能（AC#3）。

数据库文档（2026-09-13）：新增 storage/report.py 自动生成 doc-17（表清单与作用/字段与类型/依赖关系）；随字典与 schema 变更重新生成。评审修复：ref 表索引保留、DDL 审计清单仅记录实际执行语句、event_time 缺失显式报错。

真实库集成（2026-09-13）：PostgreSQL 17.9 + TimescaleDB 2.26.3（192.168.18.10；DHCP 地址会变，env DATABASE_HOST 已过期，用 FDP_DATABASE_HOST 覆盖）。已建独立库 fin_data_platform + timescaledb 扩展。验证：ensure_schema 幂等（27 条语句，5 个 hypertable + 5 个压缩策略）；幂等 append 1/0（改用 RETURNING 计数，修复 PG rowcount=-1）；as-of/latest 正确。集成中发现并修复：① ensure_schema 传 metadata 时丢失 specs（hypertable 不建）；② create_hypertable 需 migrate_data（存量表）；③ readers 增加 filters（避免子查询外过滤导致笛卡尔积）。新增 StorageConfig.from_env + tests/test_integration_storage.py（-m integration）。待办：Alembic 迁移、Parquet/CSV 导入、只读角色授权、自建 compose（TASK-3.4）。

拆分（2026-09-13）：剩余工作拆为子任务 TASK-3.3.1（Alembic 迁移）/3.3.2（Parquet-CSV 导入）/3.3.3（只读角色授权）；本任务按已交付核心收口。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
存储层核心落地：字典→schema（含 Timescale DDL）、幂等写入（RETURNING 计数）、as-of/latest 读取；真实 PG17+TimescaleDB 验证（5 hypertable + 5 压缩策略、幂等 1/0）；集成测试基建；剩余拆至 3.3.1~3.3.3。
<!-- SECTION:FINAL_SUMMARY:END -->
