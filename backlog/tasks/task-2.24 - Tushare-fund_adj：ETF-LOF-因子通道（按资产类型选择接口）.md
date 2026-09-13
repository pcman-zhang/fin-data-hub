---
id: TASK-2.24
title: Tushare fund_adj：ETF/LOF 因子通道（按资产类型选择接口）
status: Done
assignee: []
created_date: '2026-09-13 11:03'
updated_date: '2026-09-13 11:08'
labels: []
dependencies:
  - TASK-2.21
parent_task_id: TASK-2
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
实测：Tushare adj_factor 仅股票；ETF/LOF 因子在 fund_adj（510300.SH/161725.SZ 各 654 行）。任务：TushareAdapter.fetch_adjust_factors 按 sec_type 选择接口（stock→adj_factor；etf/lof→fund_adj）；场外基金/指数无因子应明确 UnsupportedCapability；测试（fixture）+ 文档（doc-8 §3.1 矩阵、doc-2 §6.16）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TushareAdapter 按资产类型调用 adj_factor / fund_adj，输出统一 code/date/adj_factor
- [x] #2 无因子组合明确报错（不得静默回退）；含测试
- [x] #3 文档与覆盖矩阵同步（doc-8/doc-2）
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现与验证（2026-09-13）：
- TushareAdapter.fetch_adjust_factors 按资产类型分组选择接口：stock→adj_factor；etf/lof→fund_adj；场外基金/指数显式 UnsupportedCapability（不静默回退）。
- 实测佐证：510300.SH/161725.SZ 各 654 行（fund_adj）；场外 000001.OF、指数 000300.SH 为空。
- 测试：test_tushare_factor_endpoint_by_asset_type、test_tushare_factor_unsupported_asset_raises；全量 237 passed。
- 文档：doc-8 §3.1 覆盖矩阵、doc-2 §6.16、doc-5 §3。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Tushare 因子按资产类型选接口（股票 adj_factor、ETF/LOF fund_adj、其余显式报错），统一输出 code/date/adj_factor；测试与文档矩阵同步，全量 237 passed。
<!-- SECTION:FINAL_SUMMARY:END -->
