---
id: TASK-2.21
title: FinDataHub Router 层：跨 adapter 组合（raw + factor 复权合成）
status: Done
assignee: []
created_date: '2026-09-13 10:00'
updated_date: '2026-09-13 10:11'
labels: []
dependencies:
  - TASK-2.16
documentation:
  - backlog/docs/architecture/doc-5 - FinDataHub-Router-Policy（复权路由策略）.md
parent_task_id: TASK-2
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-2 §6.16：在 FinDataHub 增加 Router 层，一次请求可组合多个 adapter。复权场景：raw 数据取自请求源（如 Fuyao），因子取自配置的因子源（默认 Tushare），Hub 按 qfq/hfq 计算复权价（不依赖厂商预计算复权）。RoutingConfig 可配置因子源与"可信原生复权源"；可信源仍走原生复权。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 RoutingConfig（factor_source/trusted_native_adjust）与 HubConfig.routing 落地
- [x] #2 TushareAdapter.fetch_adjust_factors（adj_factor → code/date/adj_factor）与 CAP_ADJUST_FACTORS
- [x] #3 facade.get_bars：非可信源 + adjust 时组合 raw + factor 合成复权；attrs 标注 factor_source；可信源走原生复权
- [x] #4 测试：hfq/qfq 合成、可信源原生路径、因子缺失报错、禁用路由报错；文档同步（doc-1/doc-2/README）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. routing.py（RoutingConfig + apply_adjustment）；2. base/capabilities/tushare 增加因子能力；3. facade 组合路径；4. tests/test_routing.py；5. 文档同步；6. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
策略文档：doc-5（规则/配置/溯源/原因/扩展）。

验证：tests/test_routing.py 10 项；全库 196 passed；ruff/mypy 全过。实现：routing.py（RoutingConfig/BarsPlan/字段补全/复权合成）；TushareAdapter.fetch_adjust_factors + CAP_ADJUST_FACTORS；facade.get_bars 执行计划（主源→回退链→字段补全→因子合成）+ 溯源 attrs（source/requested_source/factor_source/filled_from）；回退仅对 SourceError/MissingCredentialError 生效（RateLimitTimeout 直接抛出）。策略文档 doc-5；doc-1/doc-2/README 同步。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 Router 顶层路由：统一输出下的主源执行、字段补全（fallback coalesce）、raw+factor 复权合成、主源失败回退与溯源标注；可配置 RoutingConfig。验证：全库 196 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
