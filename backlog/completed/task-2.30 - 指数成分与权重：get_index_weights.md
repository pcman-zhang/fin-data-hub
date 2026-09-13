---
id: TASK-2.30
title: 指数成分与权重：get_index_weights
status: Done
assignee: []
created_date: '2026-09-13 11:30'
updated_date: '2026-09-13 11:43'
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
- [x] #1 get_index_weights 输出 code/date/con_code/weight 规范列，日期与权重类型正确
- [x] #2 多指数分块与空结果处理有测试；spec 覆盖
- [x] #3 doc-6 契约增补；全量测试与 ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. probe index_weight 行为（单/多指数、字段、频率）；2. Capability.INDEX_WEIGHTS + BaseAdapter + capabilities 表；3. INDEX_WEIGHT_COLUMNS + tushare spec [response.index_weights]；4. adapter fetch_index_weights（逐指数）+ facade get_index_weights；5. 测试（adapter+facade）；6. doc-6/README；7. 全量测试 + 实时冒烟 + 收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PIT 语义（2026-09-13）：index_weight 为月度快照型，as-of 取 trade_date <= as_of 的最近一期；需保留全部快照（不可只看最新），用于成分差分与权重还原。

实现与验证（2026-09-13）：
- 新增 Capability.INDEX_WEIGHTS + spec [response.index_weights]（index_code/trade_date/con_code/weight）。
- adapter fetch_index_weights：单指数逐次调用（实测多代码返回 0），非指数代码明确报错；facade get_index_weights（capability 分块 + 缓存）。
- 实时冒烟：000300.SH + 399006.SZ（20260801-20260911）→ 400 行（300+100），快照日 2026-08-31；多指数正确。
- 全量 256 tests passed；ruff/mypy clean；doc-6/README 契约同步。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
新增 get_index_weights（月度成分权重快照，单指数调用+多指数分块）；spec/测试/契约文档同步；实时验证沪深300+创业板指 400 行，256 tests/ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
