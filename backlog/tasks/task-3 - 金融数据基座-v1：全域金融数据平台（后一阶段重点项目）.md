---
id: TASK-3
title: 金融数据基座 v1：全域金融数据平台（后一阶段重点项目）
status: To Do
assignee: []
created_date: '2026-09-13 05:59'
updated_date: '2026-09-13 06:08'
labels: []
milestone: m-0
dependencies: []
documentation:
  - backlog/docs/roadmap/doc-2 - 金融数据基座-v1-规划（后一阶段重点项目）.md
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
将 v0 采集库演进为带数据库的全域金融数据平台（后一阶段研发重点项目）：对外 FinDataPlatform HTTP REST（版本化 + OpenAPI）；内部 DataPanel 数据平面（PIT 双时间轴、as-of 与重述）；DataSource/Adapter 插件化扩展（含 BaoStock 等）；PostgreSQL + TimescaleDB；数据字典与血缘；数据质量检查；Docker 独立部署；采集调度；管理型 WebUI。规划与架构决策见 doc-2。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 平台架构设计完成并通过评审（存储模型/数据字典规范/部署拓扑/服务形态）
- [ ] #2 数据字典与血缘覆盖首批数据域（含来源/约束/单位/派生指标公式）
- [ ] #3 PostgreSQL 存储层可幂等重建全量、增量同步可重复执行
- [ ] #4 docker compose 一键部署（含数据库），配置与凭证注入不落镜像
- [ ] #5 数据质量检查每日产出报告，关键指标跨源对账通过率 100%
<!-- AC:END -->
