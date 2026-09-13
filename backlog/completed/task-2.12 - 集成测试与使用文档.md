---
id: TASK-2.12
title: 集成测试与使用文档
status: Done
assignee: []
created_date: '2026-09-12 12:02'
updated_date: '2026-09-12 13:00'
labels: []
dependencies:
  - TASK-2.6
  - TASK-2.7
  - TASK-2.8
  - TASK-2.9
parent_task_id: TASK-2
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
标记 integration 的端到端测试（凭证可用时运行）；使用文档与 README 更新为可用状态；各源支持范围与限制说明。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 pytest -m "not integration" 离线全绿；integration 默认跳过
- [x] #2 文档示例与实际 API 一致，标注各源支持范围与限制
- [x] #3 测试断言无持久化写盘
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. sources/factory.py + DataHub.from_config：按配置最佳努力构建注册表（有凭证才注册，AkShare 尝试 import）；2. pyproject addopts 默认排除 integration；3. tests/test_integration.py：凭证缺失自动 skip 的四源端到端（标记 integration）+ tests/test_no_persistence.py；4. tests/test_factory.py；5. README 更新为可用状态（from_config、能力矩阵、限制、凭证 env、开发命令）；6. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：默认 pytest 151 passed / 4 deselected（integration 自动排除）；pytest -m integration --collect-only 收集 4 项；ruff/mypy 全过。新增：sources/factory.py + DataHub.from_config（按配置自动装配、缺凭证/依赖跳过）；tests/test_factory.py、tests/test_no_persistence.py、tests/test_integration.py（凭证缺失 skip）；README 重写为可用状态（from_config、能力矩阵、限制、凭证、缓存、计量、开发命令）；按用户要求加入 MIT LICENSE 与 pyproject license/license-files。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成集成测试与文档：integration 标记默认跳过（pytest -m integration 运行）、四源端到端测试按凭证自动 skip、无持久化写盘断言；DataHub.from_config 自动装配；README 更新为可用状态并新增 MIT LICENSE。验证：151 项离线单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
