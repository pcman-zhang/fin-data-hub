---
id: TASK-2.25
title: Tushare ETF/LOF 与指数行情：bars 按资产类型路由（fund_daily/index_daily）
status: Done
assignee: []
created_date: '2026-09-13 11:21'
updated_date: '2026-09-13 11:22'
labels: []
dependencies:
  - TASK-2.24
parent_task_id: TASK-2
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
实测：Tushare daily 仅股票（ETF 510300.SH 返回 0 行）；ETF/LOF 行情走 fund_daily、指数走 index_daily（均含 open/high/low/close/vol/amount）。且 fetch_bars(adjust=qfq/hfq) 复权因子写死 adj_factor，ETF/LOF 需 fund_adj（TASK-2.24 只改了独立的 fetch_adjust_factors）。任务：fetch_bars 按 sec_type 分组路由行情接口与因子接口；指数无复权因子需明确报错；测试（fake + 金样）+ 实时冒烟；覆盖矩阵文档更新。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 fetch_bars 按 sec_type 路由：stock→daily、etf/lof→fund_daily、index→index_daily；混合请求分组查询；.OF 等不支持类型明确报错
- [x] #2 bars 复权路径按资产类型取因子（stock→adj_factor；etf/lof→fund_adj）；指数复权明确 UnsupportedCapability
- [x] #3 测试覆盖路由/复权/报错 + 实时冒烟；全量测试与 ruff/mypy 通过
- [x] #4 文档更新：行情/因子覆盖矩阵（doc-8 §3.1、README 源说明）
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现与验证（2026-09-13）：
- fetch_bars 按 sec_type 分组：stock→daily、etf/lof→fund_daily、index→index_daily；.OF 明确 UnsupportedCapability；混合请求单次分组查询。
- bars 复权复用 fetch_adjust_factors（stock→adj_factor；etf/lof→fund_adj；index/场外无因子报错）。
- 测试：路由（3 类混查）、ETF qfq 走 fund_adj、指数复权拒绝、场外行情拒绝；实时冒烟——ETF/LOF/指数各 9 行、混合 27 行、ETF qfq 正常。
- 全量 247 tests passed；ruff/mypy clean。文档：doc-8 §3.1 行情矩阵、README 源说明。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Tushare 行情按资产类型路由（daily/fund_daily/index_daily），bars 复权因子按类型选择（adj_factor/fund_adj），指数/场外明确报错；测试与实时冒烟通过，247 tests + ruff/mypy 干净，文档矩阵同步。
<!-- SECTION:FINAL_SUMMARY:END -->
