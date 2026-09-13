---
id: TASK-2.29
title: 事件数据：get_market_events（ipo/suspension/st）
status: To Do
assignee: []
created_date: '2026-09-13 11:30'
updated_date: '2026-09-13 11:36'
labels: []
dependencies:
  - TASK-2.18
parent_task_id: TASK-2
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
新增 get_market_events(*, kind="ipo"|"suspension"|"st", start, end, codes=None)：ipo→new_share；suspension→suspend_d；st→stock_st。统一返回规范列（按 kind 定义 schema），支持日期区间与可选代码过滤；spec + 测试 + doc-6 增补。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 get_market_events 三 kind 输出各自规范 schema（doc-6 增补）
- [ ] #2 日期区间/代码过滤语义与测试覆盖；空结果与非法 kind 明确报错
- [ ] #3 全量测试与 ruff/mypy 通过
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PIT 关联（2026-09-13）：名称变更历史（Tushare namechange）对 as-of 宇宙/标的属性还原必需；当前 scope 为 ipo/suspension/st，是否将 namechange 纳入本任务待确认（或单独任务）。
<!-- SECTION:NOTES:END -->
