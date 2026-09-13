---
id: TASK-2.29
title: 事件数据：get_market_events（ipo/suspension/st）
status: Done
assignee: []
created_date: '2026-09-13 11:30'
updated_date: '2026-09-13 11:50'
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
- [x] #1 get_market_events 三 kind 输出各自规范 schema（doc-6 增补）
- [x] #2 日期区间/代码过滤语义与测试覆盖；空结果与非法 kind 明确报错
- [x] #3 全量测试与 ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. probe new_share/suspend_d/stock_st/st 参数与多代码；2. 定义三 kind 规范列（ipo/suspension/st）；3. Capability.MARKET_EVENTS + spec 映射 + schemas；4. adapter fetch_market_events + facade get_market_events；5. 测试 + doc-6/README；6. 全量测试/冒烟/收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PIT 关联（2026-09-13）：名称变更历史（Tushare namechange）对 as-of 宇宙/标的属性还原必需；当前 scope 为 ipo/suspension/st，是否将 namechange 纳入本任务待确认（或单独任务）。

实现与验证（2026-09-13）：
- get_market_events：ipo→new_share、suspension→suspend_d、st→stock_st（st 接口无权限，改用日频 stock_st）。
- 分页保护（limit/offset，1000/页，最多 50 页）；codes 过滤：ipo/st 本地、suspension 源端。
- 规范列：ipo 11 列、suspension 4 列、st 5 列（+currency 门面派生）。
- 实时冒烟：ipo 27 行（2025Q1）、suspension 272 行（2025-01，S 244/R 28）、st 865 行（5 日×~173）。
- 全量 267 tests passed；ruff/mypy clean；doc-6/README 契约同步。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
新增 get_market_events（ipo/suspension/st，分页取全量 + codes 过滤）；实测 new_share/suspend_d/stock_st 均正常（27/272/865 行），267 tests/ruff/mypy 全绿，契约文档同步。
<!-- SECTION:FINAL_SUMMARY:END -->
