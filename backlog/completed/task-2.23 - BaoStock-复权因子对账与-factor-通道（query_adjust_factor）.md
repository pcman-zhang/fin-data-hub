---
id: TASK-2.23
title: BaoStock 复权因子对账与 factor 通道（query_adjust_factor）
status: Done
assignee: []
created_date: '2026-09-13 10:58'
updated_date: '2026-09-13 11:08'
labels: []
dependencies:
  - TASK-2.22
parent_task_id: TASK-2
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
BaoStock 提供免费复权因子（query_adjust_factor，涨跌幅复权算法）。任务：① 与 Tushare adj_factor / 标准公式逐事件对账（doc-4 方法）；② 通过后实现 BaoStockAdapter.fetch_adjust_factors 并评估是否纳入 Router factor_source；③ 未通过则记录结论与限制（仅不参与路由）。参考 doc-7。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 对账实验完成：raw×factor、事件乘数 vs 理论、与 Tushare 因子差异统计（重叠期）
- [x] #2 结论入档（doc-7/doc-4 风格）；通过则实现 fetch_adjust_factors + 测试；未通过则明确禁用条件
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
对账完成（2026-09-13，R2=doc-9；说明=doc-8）：原始价最大差 0；因子归一化比 0.999998（std 6.5e-06）；事件乘数差 ≤4.6 ppm；qfq 自洽 1.000000；hfq 仅锚点差（常数 ≈0.887，跨源不可直接比较）。结论：通过，可作为 factor_source（默认仍 Tushare）。文档：R1=doc-4、R2=doc-9、说明=doc-8。下一步：实现 BaoStockAdapter.fetch_adjust_factors（事件步进 + 基准行）。

覆盖范围实测（2026-09-13）：BaoStock query_adjust_factor 仅股票；ETF/LOF/指数为空。因此 BaoStock factor 通道限定股票；ETF/LOF 因子须走 Tushare fund_adj（见 TASK-2.24）。

实现与验证（2026-09-13）：
- BaoStockAdapter.fetch_adjust_factors：单代码；固定自 1990-01-01 回看；输出 = 窗口基准行（start，取最近历史事件累计因子；无历史则为 1.0）+ 窗口内事件行（dividOperateDate + backAdjustFactor）；仅股票，非股票显式 UnsupportedCapability；capabilities + capabilities.py（max_codes_per_call=1）。
- Router apply_adjustment 改为 backward merge_asof（事件步进对齐），修复稀疏因子 + 非交易日 start 的缺失报错；qfq/hfq 语义不变。
- 测试：tests/test_baostock_adapter.py（基准行/组合 qfq+hfq/拒绝）、tests/test_routing.py（SparseFactorAdapter backward 对齐 ×qfq/hfq）。全量 237 passed；ruff/mypy clean。
- 真实端到端：source=baostock + factor_source=baostock（654 天）vs BaoStock 官方复权价：qfq 0.99999997（std 3.7e-07）、hfq 1.00000000（std 9.2e-17）。
- 文档：doc-9 §E/§F、doc-7 §2.4、doc-5 §3。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
BaoStock 复权因子对账通过并落地 factor 通道：实现 fetch_adjust_factors（事件步进 + 窗口基准行，仅股票），Router 改 merge_asof 支持稀疏因子；测试 237 passed + ruff/mypy clean；真实数据端到端 vs 官方复权 qfq 1e-7 级、hfq 机器精度。
<!-- SECTION:FINAL_SUMMARY:END -->
