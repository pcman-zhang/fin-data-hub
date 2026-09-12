---
id: TASK-2.8
title: iFinD MCP 适配器（含 markdown parser）
status: To Do
assignee: []
created_date: '2026-09-12 12:01'
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
- [ ] #1 fixture（脱敏真实响应）解析为统一 schema
- [ ] #2 多标的聚合调用：一次请求多 code，不逐标的拆分
- [ ] #3 EDB 一次一指标的限制在接口层校验并报错
- [ ] #4 解析失败抛可诊断异常（含截断的原始片段）
<!-- AC:END -->
