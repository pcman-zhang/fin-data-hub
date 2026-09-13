---
id: TASK-3.3
title: TimescaleDB 存储层：schema / 分区 / 迁移 / 幂等增量
status: To Do
assignee: []
created_date: '2026-09-13 05:59'
updated_date: '2026-09-13 08:18'
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
- [ ] #1 全量可幂等重建；增量重复执行结果一致
- [ ] #2 迁移脚本可版本化升级/回滚
- [ ] #3 关键查询（按标的+日期、按域）走索引且性能达标
- [ ] #4 支持用户提供历史数据文件（Parquet/CSV）幂等导入
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
存储按 PIT 分级落地：append-only 版本表 + is_latest 物化视图；复权因子版本化、复权价读时按 as-of 计算；指数成分用生效区间 + SCD2（doc-2 §6.9）。
<!-- SECTION:NOTES:END -->
