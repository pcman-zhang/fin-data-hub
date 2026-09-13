---
id: TASK-2.18
title: 归一化层：Wind 标准代码映射 + 请求参数转换 + 响应归一化（spec 驱动）
status: In Progress
assignee: []
created_date: '2026-09-13 08:41'
updated_date: '2026-09-13 10:50'
labels: []
dependencies:
  - TASK-2.2
documentation:
  - backlog/docs/architecture/doc-6 - 归一化层与-FinDataHub-API-契约设计.md
parent_task_id: TASK-2
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-6 设计落地归一化层：先冻结 FinDataHub API 契约与 canonical schema，再实现（1.1）请求侧映射（Wind 标准 venue：.SH/.SZ/.BJ/.OF/.CSI/.HK/.O/.N/.A/.GI/.TI/.WI；CodeMapper + 参数映射）与（1.2）响应侧归一化（字段/单位/枚举/日期/代码 canonical 化，spec 驱动 TOML，CI 覆盖度 + 金样对照）；阶段 A 契约+spec 框架 → B adapter 切换 → C 扩展（BaoStock/HK/US）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 SecCode/SecType 支持 Wind 标准 venue（含 .O/.N/.A/.GI/.TI/.WI）与指数类型；映射往返测试通过
- [ ] #2 各源 CodeMap 覆盖 HK/US/指数/自定义指数；不支持场景有明确映射或可诊断报错
- [ ] #3 请求参数转换与响应归一化 spec 化（机读文件）+ 覆盖度校验
- [ ] #4 与平台数据字典一致性校验（CI）；全量测试通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
阶段A：1. enums（Venue/Currency/Adjust/Freq/ReferenceKind/Capability）+ constants（attrs 键、VENUE_CURRENCY）；2. codes 切换 Venue、schemas 增加 currency 推导、Capability 替换 CAP_*；3. spec 框架（specs/*.toml + loader/validator/normalize + 覆盖度测试）；4. facade 实现 get_adjust_factors/get_adjustment_events + 预留接口；5. pytest/ruff/mypy 全绿；阶段B（adapter 切换）后续任务。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fuyao 字段/单位/枚举映射（doc-3 §2）作为映射 spec 首批输入。

边界决策（2026-09-13）：v0 不引入 Pydantic；归一化契约靠类型签名 + doc-6 + 显式校验 + 金样测试；spec 用 tomllib + 显式校验。Pydantic 归属 v1 FinDataPlatform SDK/REST。

契约决策（2026-09-13）：① venue Wind 标准；② daily_return 百分比；③ spec 每源一个 TOML（tomllib）；④ API/schema 冻结（只增不改）。新增预留接口 get_intraday_bars / get_edb_series（调用抛 UnsupportedCapability）；货币口径：新增 currency 列（ISO 4217，按 venue 推导；GI 需参考数据）；待确认补充 get_adjust_factors / get_adjustment_events。

契约最终确认（2026-09-13）：get_adjust_factors/get_adjustment_events 纳入冻结契约；新增全局枚举（Venue/Currency/Adjust/Freq/ReferenceKind/Capability）与 constants.py（attrs 键、VENUE_CURRENCY）；公共参数接受 枚举|字符串 并 coerce；spec 枚举校验；v1 复用同一批枚举（doc-6 §8/§9）。

阶段 A 完成（2026-09-13）：枚举/常量/Venue 化/currency 列/spec 框架（4 源 TOML + loader/validator/normalize + 覆盖度测试）/facade 新方法 + 预留接口；全库测试通过（ruff/mypy 干净）。阶段 B（adapter 切换 normalize + 金样对照）与阶段 C（BaoStock/HK/US）待做。
<!-- SECTION:NOTES:END -->
