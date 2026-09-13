---
id: TASK-2.22
title: BaoStock 适配器（免费源）
status: Done
assignee: []
created_date: '2026-09-13 10:52'
updated_date: '2026-09-13 10:58'
labels: []
dependencies:
  - TASK-2.21
parent_task_id: TASK-2
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
接入免费源 BaoStock（baostock 包）：bars（日线，原生 adjustflag 1/2/3；代码 sh.600000 格式，映射层转换；volume=股、amount=元）、reference（query_stock_basic → stock_list）、trade_calendar（query_trade_dates）；会话 login/logout 生命周期与线程安全；错误码映射；默认限流。Router 默认先排除付费源：trusted_native_adjust 去掉 Wind（iFinD 本就不在），BaoStock 暂不列入 trusted（复权走 raw+factor 合成）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Source.BAOSTOCK、BaoStockConfig、factory 注册、extras [baostock]
- [x] #2 BaoStockMapper：canonical ↔ sh./sz. 代码（含指数）；BJ 不支持明确报错
- [x] #3 适配器：bars/reference/trade_calendar + 会话管理 + 错误映射 + 测试（注入 fake 模块）
- [x] #4 Router 默认 trusted_native_adjust 去掉 Wind；集成测试（integration 标记）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Router 默认排除 Wind；2. Source/配置/限流/capabilities/extras；3. mapping BaoStockMapper；4. sources/baostock.py（注入模块、登录会话、bars/reference/calendar）+ 测试；5. factory；6. 文档与集成测试；7. 验证收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_baostock_adapter.py 13 项（含线程串行、断线重登录、引用计数、错误映射）；全库 230 passed；ruff/mypy 全过。实测：login 成功；600000.SH 2026-09-01~11 日线 9 行；query_adjust_factor 可用（code/dividOperateDate/foreAdjustFactor/backAdjustFactor/adjustFactor）；logout 正常。实现：BaoStockAdapter（bars/reference/trade_calendar；模块级 RLock + 会话代际 + 引用计数；连接类失败失效会话并按退避重登录重试）；BaoStockMapper；factory/extras；集成测试。Router 默认 trusted_native_adjust 改为 {TUSHARE, AKSHARE}（排除 Wind）。文档：README/AGENTS/doc-1/doc-7。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 BaoStock 免费源适配器：bars（日线，单代码）/reference（stock_list）/trade_calendar；线程安全（全局锁 + 会话代际/引用计数）与断线自动重登录；代码映射、错误映射、限流计量；实测连通通过。验证：全库 230 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
