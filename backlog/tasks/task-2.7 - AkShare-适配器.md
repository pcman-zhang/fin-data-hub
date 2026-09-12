---
id: TASK-2.7
title: AkShare 适配器
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:29'
labels: []
dependencies:
  - TASK-2.4
parent_task_id: TASK-2
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
akshare 适配：股票/ETF/LOF/场外基金/指数行情与参考数据；按 endpoint 映射 6 位或专有代码；默认低 QPS 保守。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 离线 fixture（monkeypatch akshare 调用）测试字段映射
- [x] #2 代码映射覆盖 stock/etf/lof/fund/index 代表端点
- [x] #3 解析异常与空结果映射为库异常/空表策略有测试
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. sources/akshare.py：AkShareAdapter（ak_module 可注入）；bars 按 sec_type 路由 stock_zh_a_hist/fund_etf_hist_em/fund_lof_hist_em/index_zh_a_hist（逐 code 调用）；fund_nav（fund_open_fund_info_em）；trade_calendar（tool_trade_date_hist_sina）；中文列名映射、手→股、异常映射；2. tests/test_akshare_adapter.py 用 FakeAkModule 覆盖路由/映射/空结果/异常；3. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_akshare_adapter.py 12 项；全库 103 passed；ruff/mypy 全过。实现：bars 按 sec_type 路由 4 个 endpoint（逐 code 调用）、fund_nav（单位净值走势，日增长率映射，区间过滤）、trade_calendar（tool_trade_date_hist_sina 构造连续日历）、中文列名映射、手→股、ak_module 可注入、空结果保持 schema；capabilities={bars,fund_nav,trade_calendar}。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 AkShare 适配器：股票/ETF/LOF/指数 K 线路由、场外基金净值、交易日历；字段与单位统一、异常映射、离线 FakeAkModule 测试 12 项。验证：全库 103 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
