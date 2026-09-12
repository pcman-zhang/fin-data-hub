---
id: TASK-2.9
title: Wind MCP 适配器（get 优先）
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:42'
labels: []
dependencies:
  - TASK-2.4
  - TASK-2.5
parent_task_id: TASK-2
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Wind 7 服务适配高频端点；get 类工具优先，精确代码批量；EDB get_economic_data 批量；债券长区间分块；解析 {date, indicatorInfo} 结构。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 fixture 测试覆盖 K线/快照/EDB/债券
- [x] #2 批量分块逻辑有单测（超过 50 代码、超过 90 天区间自动分批）
- [x] #3 不调用 query 类工具
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 实测确认 Wind 响应结构（kline/snapshot 的 data.columns/rows/unit；period=1d 被后端拒绝→日线省略 period）；2. sources/wind.py：WindAdapter（7 服务端点、客户端可注入、Wind 表解析与单位换算、bars 按 sec_type 路由 per-code、snapshot 批量 ≤50、adjust→aftype、EDB get_economic_data 批量、债券 ≤90 天分块+中文日期）；3. tests/test_wind_adapter.py：脱敏实测 fixture（kline/snapshot）+ EDB/债券结构 fixture；4. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_wind_adapter.py 13 项；全库 128 passed；ruff/mypy 全过。实测确认：后端不接受 period=1d（日线省略 period）；kline 列为 TIME/OPEN/MATCH/HIGH/LOW/TURNOVER/VOLUME；snapshot 为 data.columns/rows/unit（含 Wind代码）。实现：7 服务端点、客户端可注入、Wind 表+单位换算、bars per-code 路由（stock/fund/index）、snapshot 分组 + >50 自动分批、EDB get_economic_data 批量（get 优先，不调 query 类）、债券 ≤90 天分块与中文日期。为确认结构实际调用 Wind get 类接口 2 次。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 Wind MCP 适配器：K 线（单代码逐次、日线省略 period、aftype 映射）、快照（≤50 分批）、EDB 精确代码批量、债券长区间分块。验证：全库 128 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
