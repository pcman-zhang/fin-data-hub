---
id: TASK-2.30
title: 指数成分与权重：get_index_weights
status: To Do
assignee: []
created_date: '2026-09-13 11:30'
updated_date: '2026-09-13 11:36'
labels: []
dependencies:
  - TASK-2.25
parent_task_id: TASK-2
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
新增 get_index_weights(index_codes, *, start, end)：Tushare index_weight（月度成分权重）。规范列 code/date/con_code/weight；支持多指数（分块）；spec + 测试 + doc-6 增补。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 get_index_weights 输出 code/date/con_code/weight 规范列，日期与权重类型正确
- [ ] #2 多指数分块与空结果处理有测试；spec 覆盖
- [ ] #3 doc-6 契约增补；全量测试与 ruff/mypy 通过
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PIT 语义（2026-09-13）：index_weight 为月度快照型，as-of 取 trade_date <= as_of 的最近一期；需保留全部快照（不可只看最新），用于成分差分与权重还原。
<!-- SECTION:NOTES:END -->
