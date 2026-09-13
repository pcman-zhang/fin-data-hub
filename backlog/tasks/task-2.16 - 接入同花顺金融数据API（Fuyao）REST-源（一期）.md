---
id: TASK-2.16
title: 接入同花顺金融数据API（Fuyao）REST 源（一期）
status: To Do
assignee: []
created_date: '2026-09-13 05:52'
labels: []
dependencies: []
references:
  - 'https://fuyao.aicubes.cn/docs/api-reference/overview/'
  - 'https://fuyao.aicubes.cn/llms-full.txt'
parent_task_id: TASK-2
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
新增数据源 Source.FUYAO（thscode 与 canonical WindCode 一致，可直通）。接入方式：REST 直连 https://fuyao.aicubes.cn（请求头 X-api-key），不依赖源码 SDK 与本地 marketdb（与“无存储层”约束一致；服务同时提供 MCP，可选后续）。一期能力：bars（A股/指数历史K线，单标的）、snapshot（按 thscodes 批量）、reference（标的检索/代码表）、trade_calendar（近一年）。响应信封 {code,message,request_id,data:{timestamp,item}}；错误码映射：1001~1004→ValueError、2001→MissingCredentialError、2003→UnsupportedCapability、3001/3002/3004→SourceError、4001/HTTP429→RateLimitError（退避重试）、5xxx→SourceError。服务当前免费且不限累计次数，但动态限流：默认 QPS 保守（2）可配置；capability cost_class=free。配置：FuyaoConfig(api_key) + HubConfig.fuyao + factory 注册 + extras [fuyao]（httpx）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Source.FUYAO、FuyaoConfig、HubConfig.fuyao、extras [fuyao] 与 factory 注册落地；缺凭证抛 MissingCredentialError
- [ ] #2 FuyaoAdapter 实现 bars/snapshot/reference/trade_calendar 四能力；thscode 直通；响应信封与错误码映射（含 4001/429 退避重试）
- [ ] #3 默认限流（2 QPS，可覆盖）与用量计量复用 BaseAdapter 机制；capability 表 cost_class=free
- [ ] #4 fixture 测试覆盖成功信封/错误码/字段与单位映射；integration 测试按 FIN_DATA_HUB_FUYAO_API_KEY 自动 skip
- [ ] #5 README 支持矩阵与凭证说明、doc-1 数据源章节更新；注明当前免费与动态限流
<!-- AC:END -->
