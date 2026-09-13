---
id: TASK-2.6
title: Tushare 适配器
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:29'
labels: []
dependencies:
  - TASK-2.4
parent_task_id: TASK-2
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
tushare 包适配高频端点：股票/指数/ETF 日线、快照、场外基金净值、参考数据（股票/基金/指数列表、交易日历）；代码直通；字段映射到统一 schema；token 配置注入。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 离线 fixture 测试字段映射与类型统一
- [x] #2 缺 token 抛 MissingCredentialError；不隐式读取任何配置
- [x] #3 adjust 口径（None/qfq/hfq）实现并与文档一致，有测试
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. sources/tushare.py：TushareAdapter（注入 api，token 缺失抛 MissingCredentialError）；bars（daily + adj_factor 计算 qfq/hfq；vol*100 股、amount*1000 元）、fund_nav（按 code 计算 daily_return）、reference（stock/fund/index_basic）、trade_calendar；2. tests/test_tushare_adapter.py 覆盖映射/复权/错误/缺 token/不支持 freq；3. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_tushare_adapter.py 13 项；全库 91 passed；ruff/mypy 全过。实现：daily+adj_factor（qfq=price*factor/latest、hfq=price*factor）、单位统一（手→股、千元→元）、fund_nav 按 code 计算日增长率、stock/fund/index_basic、trade_cal；api 可注入便于离线测试；capabilities 不含 snapshot。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 Tushare 适配器：bars（含 qfq/hfq）、fund_nav、reference（stock/fund/index）、trade_calendar；token 缺失抛 MissingCredentialError，API 异常映射 SourceError。验证：91 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
