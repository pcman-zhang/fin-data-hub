---
id: TASK-3.14
title: Security Master 落地：标的注册与多源代码映射
status: To Do
assignee: []
created_date: '2026-09-13 12:16'
updated_date: '2026-09-13 12:56'
labels: []
milestone: m-0
dependencies: []
parent_task_id: TASK-3
ordinal: 50000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-10 §3.3 落地平台基石：security_id 主键；security_alias（多源代码 + 有效期）；security_status_history（上市/暂停/退市）；security_attribute_history（名称/ST/类型 SCD2）；含退市永久保留；as-of 宇宙查询；DataPanel 强制挂载 security_id；从 FinDataHub 基础信息（stock/fund/etf/index + delist_list + namechange）构建与刷新；与 TASK-3.2 字典、TASK-3.3 存储联动。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 四张逻辑表 schema 与迁移落地；security_id 生成与多源别名（source+source_code → security_id）查询可用
- [ ] #2 as-of 宇宙查询（含退市）与 SCD2 属性还原（名称/状态）测试通过
- [ ] #3 构建/刷新流程对接 FinDataHub（含 delist_list/namechange）；字典条目与文档同步
<!-- AC:END -->
