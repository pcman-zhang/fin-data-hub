---
id: TASK-2.16
title: 接入同花顺金融数据API（Fuyao）REST 源（一期）
status: Done
assignee: []
created_date: '2026-09-13 05:52'
updated_date: '2026-09-13 09:21'
labels: []
dependencies: []
references:
  - 'https://fuyao.aicubes.cn/docs/api-reference/overview/'
  - 'https://fuyao.aicubes.cn/llms-full.txt'
documentation:
  - backlog/docs/integrations/doc-3 - Fuyao-REST-API-接入参考（开发用）.md
parent_task_id: TASK-2
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
新增数据源 Source.FUYAO（thscode 与 canonical WindCode 一致，可直通）。接入方式：REST 直连 https://fuyao.aicubes.cn（请求头 X-api-key），不依赖源码 SDK 与本地 marketdb（与“无存储层”约束一致；服务同时提供 MCP，可选后续）。一期能力：bars（A股/指数历史K线，单标的）、snapshot（按 thscodes 批量）、reference（标的检索/代码表）、trade_calendar（近一年）。响应信封 {code,message,request_id,data:{timestamp,item}}；错误码映射：1001~1004→ValueError、2001→MissingCredentialError、2003→UnsupportedCapability、3001/3002/3004→SourceError、4001/HTTP429→RateLimitError（退避重试）、5xxx→SourceError。服务当前免费且不限累计次数，但动态限流：默认 QPS 保守（2）可配置；capability cost_class=free。配置：FuyaoConfig(api_key) + HubConfig.fuyao + factory 注册 + extras [fuyao]（httpx）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Source.FUYAO、FuyaoConfig、HubConfig.fuyao、extras [fuyao] 与 factory 注册落地；缺凭证抛 MissingCredentialError
- [x] #2 FuyaoAdapter 实现 bars/snapshot/reference/trade_calendar 四能力；thscode 直通；响应信封与错误码映射（含 4001/429 退避重试）
- [x] #3 默认限流（2 QPS，可覆盖）与用量计量复用 BaseAdapter 机制；capability 表 cost_class=free
- [x] #4 fixture 测试覆盖成功信封/错误码/字段与单位映射；integration 测试按 FIN_DATA_HUB_FUYAO_API_KEY 自动 skip
- [x] #5 README 支持矩阵与凭证说明、doc-1 数据源章节更新；注明当前免费与动态限流
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. enums/config/ratelimit/capabilities/pyproject 接入 Fuyao；2. sources/fuyao.py（httpx 注入、信封解析与错误码映射、bars 单标的+10年分块、snapshot 批量、reference 分页、calendar 近一年窗口）；3. factory 注册；4. tests/test_fuyao_adapter.py（MockTransport）+ 集成测试；5. 用临时 token 实测快照/日线/日历（不落盘）；6. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
开发参考 doc-3 已整理（2026-09-13）。关键约束：historical 单标的且窗口 ≤10 年（需分块合并）；snapshot 无交易日期（date 由 data.timestamp 推导）；calendar 固定近一年窗口；tickers/list 分页 limit≤10000；reference 无 industry 字段；错误码映射见 doc-3 §1。

验证：tests/test_fuyao_adapter.py 21 项（含 4001 重试、窗口分块、分页、错误码映射）；全库 187 passed；ruff/mypy 全过。真实接口验证（临时 token，仅内存、未落盘）：快照 2 条、日线 9 条（2026-09-01~11）、日历 4 天、A股代码表 5571 条；4 次调用、成本 0。实现：FuyaoAdapter（httpx 注入、信封与错误码映射、NetworkError/RateLimitError 退避重试、bars 单标的+10年分块、snapshot 批量、reference 分页、calendar 近一年窗口）；factory 注册；extras [fuyao]；文档 README/AGENTS/doc-1/doc-3 同步。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 Fuyao（同花顺金融数据API）REST 源一期：snapshot/bars/reference/trade_calendar 四能力、错误码映射与退避重试、2 QPS 默认限流与用量计量、factory 自动装配；真实接口验证通过（快照/日线/日历/代码表）。验证：全库 187 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
