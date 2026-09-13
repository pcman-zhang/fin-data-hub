---
id: TASK-2.31
title: 名称变更历史：namechange（PIT 属性还原）
status: Done
assignee: []
created_date: '2026-09-13 11:37'
updated_date: '2026-09-13 11:51'
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
- [x] #1 namechange 数据可按代码/区间查询，输出 code/name/start_date/end_date/ann_date/change_reason（生效区间 + 公告日）
- [x] #2 PIT 语义：区间重叠可还原 as-of 名称；测试覆盖
- [x] #3 doc-6 契约增补；全量测试与 ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
并入 get_market_events(kind="namechange")：spec/列/分页/区间语义（start_date/end_date + ann_date）+ 测试 + doc-6。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现与验证（2026-09-13）：
- 并入 get_market_events(kind="namechange")：namechange 单代码（多代码返回 0）→ 指定 codes 逐代码、否则全市场区间；分页保护复用。
- 规范列 code/name/start_date/end_date/ann_date/change_reason；区间为**闭区间**（end_date 含当日，NULL=至今）——与 industry_member 的 out_date 开区间不同，已在 doc-6 标注。
- 实时冒烟：600519 三段名称（贵州茅台 2001-08-27~2006-05-24 / G茅台 2006-05-25~2006-10-08 / 贵州茅台 2006-10-09~至今）；as-of 2006-06-01 还原为"G茅台"；全市场 2025H1 273 行。
- 全量 272 tests passed；ruff/mypy clean；doc-6/README 同步。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
namechange 并入 get_market_events：名称生效闭区间 + 公告日，支持 as-of 名称还原；单代码限制处理与分页复用；实测三段名称区间与 273 行全市场数据，272 tests/ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
