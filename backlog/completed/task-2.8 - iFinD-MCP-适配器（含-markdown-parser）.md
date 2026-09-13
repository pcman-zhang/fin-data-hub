---
id: TASK-2.8
title: iFinD MCP 适配器（含 markdown parser）
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:35'
labels: []
dependencies:
  - TASK-2.4
  - TASK-2.5
parent_task_id: TASK-2
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
iFinD 8 服务适配高频端点（行情/K线/快照/净值/基础资料）；markdown 表（answer）parser 转 DataFrame；按工具区分 stock/index JSON 字符串与 edb datas columns/data 结构。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 fixture（脱敏真实响应）解析为统一 schema
- [x] #2 多标的聚合调用：一次请求多 code，不逐标的拆分
- [x] #3 EDB 一次一指标的限制在接口层校验并报错
- [x] #4 解析失败抛可诊断异常（含截断的原始片段）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. mcp/parsers/markdown.py：markdown 表解析（多表、单位列名拆分与换算）；2. sources/ifind.py：IfindAdapter（服务端点表、客户端池可注入、unwrap+code 校验、聚合 NL query 一次多标的、fund_nav 双表解析、index bars 解析、EDB 单指标校验）；3. tests/test_ifind_adapter.py：脱敏 fixture（fund 双表/index 多标的/EDB 结构）+ AC 覆盖；4. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_ifind_adapter.py 15 项；全库 116 passed；ruff/mypy 全过。实现：mcp/parsers/markdown.py（多表解析、单位列名拆分与换算、find_table）；sources/ifind.py（8 服务端点表、客户端池可注入、unwrap+code 校验、多标的单次 NL 聚合、fund_nav 双表选择、index bars、EDB 单指标校验与 datas 解析）；fixture 由实测响应脱敏整理。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 iFinD MCP 适配器：fund_nav（多基金一次聚合）、指数 K 线（单位换算）、EDB 单指标查询与校验；markdown 表解析基础设施。验证：全库 116 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
