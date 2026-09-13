---
id: TASK-2.19
title: 复权因子接口对齐：raw + factor 双通道（Tushare / Fuyao）
status: Done
assignee: []
created_date: '2026-09-13 09:25'
updated_date: '2026-09-13 10:17'
labels: []
dependencies:
  - TASK-2.16
documentation:
  - >-
    backlog/docs/investigations/doc-4 -
    复权数据对账调查报告：Fuyao-vs-Tushare（600519.SH）.md
parent_task_id: TASK-2
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-2 §6.16：Hub 新增 fetch_adjust_factors——Tushare 走 adj_factor；Fuyao 走 corporate-actions/adjustment-factors（事件流，自行推导因子）。平台侧存原始价 + 因子/事件，复权价读取时按 as-of 与 adjust 计算；推导约定与源预计算复权价/Tushare 因子对账。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 FuyaoAdapter.fetch_adjust_factors：单标的、事件流映射 code/ex_date/dividend_per_share/per_share_bonus；含测试
- [x] #2 TushareAdapter.fetch_adjust_factors：adj_factor 映射 code/date/adj_factor；含测试
- [x] #3 doc-3 增补 corporate-actions 规格与复权口径；README/doc-2 同步
- [x] #4 推导约定与对账方案写入文档，纳入对账框架（TASK-2.13/3.5）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. FuyaoAdapter.fetch_adjustment_events（corporate-actions；单标的逐次、事件流 canonical：code/ex_date/dividend_per_share/per_share_bonus）；2. 测试（MockTransport fixture + 多代码逐次 + 空结果 + 参数）；3. 文档：doc-2 §6.16 因子推导约定与对账口径、README 说明；4. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
对账实验（2026-09-13，600519.SH 654 交易日）：原始价两源完全一致；Tushare adj_factor 与理论 P_prev/(P_prev−D) 一致；Fuyao backward ÷ (raw×adj_factor) 非常数（0.789~0.829），同日 OHLC 的 bwd/raw 比值不一致（open/high/low/close 各异），内部 close/open 被改变，隐含因子日常波动——Fuyao 预计算复权价不符合标准语义，不可作对账基准。平台以 raw+factor 为准；Fuyao 事件推导需逐事件对账。证据见 doc-3 §5。

完整调查报告见 doc-4（标的/范围/公式/结果/可能问题/建议）。

验证：tests/test_fuyao_adapter.py 新增 3 项（事件映射/逐代码调用/空结果/非 factor_source）；全库 199 passed；ruff/mypy 全过。实现：FuyaoAdapter.fetch_adjustment_events（事件流 canonical；接口单标的→逐代码；不作为 Router factor_source）；Tushare fetch_adjust_factors 已于 TASK-2.21 完成。文档：doc-2 §6.16 推导约定（m=P_prev(1+B)/(P_prev−D)、统一锚点、逐事件对账）、doc-3 §5 增补事件流接口。AC1 方法命名为 fetch_adjustment_events（语义更准确，输出列与 AC 一致）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成复权因子双通道：Tushare adj_factor（Router 因子源，2.21 交付）+ Fuyao 事件流 fetch_adjustment_events（推导/对账用）；推导约定与对账口径入档。验证：全库 199 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
