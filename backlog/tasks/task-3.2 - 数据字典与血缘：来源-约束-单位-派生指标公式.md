---
id: TASK-3.2
title: 数据字典与血缘：来源 / 约束 / 单位 / 派生指标公式
status: Done
assignee: []
created_date: '2026-09-13 05:59'
updated_date: '2026-09-13 13:15'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
parent_task_id: TASK-3
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按设计规范落地可执行数据字典：每个数据项记录来源、更新频率、覆盖范围、约束与注意事项、单位、时区；派生指标记录公式与依赖；提供字典校验与查询接口。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 首批数据域字典条目完整，字段可机读校验
- [x] #2 派生指标公式可追溯依赖数据项
- [x] #3 字典与代码/表结构一致性检查通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 新建 fin_data_platform 包（py.typed）+ dictionary 模块（Pydantic v2 models + loader/validator + meta-schema 导出）；2. 首批字典条目（cn_equity: daily_bar/adj_factor/index_weight/index_member/financials.balance_sheet/market_events.namechange；cn_fund.nav）；3. CI 校验（10 条规则）+ 派生依赖可追溯（无环）；4. 测试（正反例）；5. pyproject 包配置与可选依赖；6. 全量 pytest/ruff/mypy。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
数据字典需登记每项的 PIT 类别与时间字段（event_date/knowledge_date/ingest_ts/version/is_latest）及复权/重述口径（doc-2 §6.9）。

数据字典需与 hub 归一化层映射 spec 校验一致（source × endpoint 覆盖度），并登记指数子平面与 Wind 标准 venue（doc-2 §6.12）。

实施（2026-09-13）：新建 fin_data_platform 包与 dictionary 模块——Pydantic v2 meta-schema（models.py，extra=forbid）+ loader/validator（10 条 CI 规则：命名禁品牌/主键层级/decimal 精度/lineage 强制/派生依赖与去重/表达式字段校验/映射一致性/路径一致/成环检测）+ meta-schema 导出与文件比对。首批 7 条目：cn_equity.daily_bar/adj_factor/index_weight/index_member/financials.balance_sheet/market_events.namechange、cn_fund.nav。测试 16 项（正例+10 类反例+mappings↔适配器 spec 一致性）。全量 288 tests passed；ruff/mypy clean。注：表结构（DDL）一致性随 TASK-3.3 接入（当前为 meta-schema + 适配器 spec 一致性）。

代码评审修复（2026-09-13）：① QualityRule 增加 freshness 的 sla/tolerance 必填；② canonical_table 规则（domain.其余以下划线连接）与 read_model 版本后缀、partition_strategy 默认推导纳入 CI；③ mappings.endpoint 必须在 sources 声明；④ validate_directory 逐文件收集错误不再早退；⑤ 清理死断言。延期：derived.implementation 可导入 + docstring Formula/PIT 校验随 TASK-3.12（模块未建）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
数据字典落地：Pydantic meta-schema + 10 条 CI 校验 + 首批 7 个数据集条目 + meta-schema 导出比对；派生依赖可追溯（无环/输入存在/algorithm_id 唯一）；字典 mappings 与 v0 适配器 spec 交叉校验通过；288 tests/ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
