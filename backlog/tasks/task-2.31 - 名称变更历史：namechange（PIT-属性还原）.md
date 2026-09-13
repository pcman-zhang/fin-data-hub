---
id: TASK-2.31
title: 名称变更历史：namechange（PIT 属性还原）
status: To Do
assignee: []
created_date: '2026-09-13 11:37'
labels: []
dependencies:
  - TASK-2.29
parent_task_id: TASK-2
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tushare namechange：code/name/start_date/end_date/ann_date/change_reason。作为 PIT 标的属性（曾用名/ST 更名）的生效区间数据，供 as-of 还原（doc-2 §6.9）。实现形态建议并入 get_market_events(kind="namechange")（与 TASK-2.29 统一事件接口一致），或按评估独立方法；需要 spec/测试/文档。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 namechange 数据可按代码/区间查询，输出 code/name/start_date/end_date/ann_date/change_reason（生效区间 + 公告日）
- [ ] #2 PIT 语义：区间重叠可还原 as-of 名称；测试覆盖
- [ ] #3 doc-6 契约增补；全量测试与 ruff/mypy 通过
<!-- AC:END -->
