---
id: TASK-2.17
title: 对外门面更名：DataHub → FinDataHub（保留兼容别名）
status: Done
assignee: []
created_date: '2026-09-13 08:24'
updated_date: '2026-09-13 09:11'
labels: []
dependencies:
  - TASK-2.4
parent_task_id: TASK-2
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按系统分层定稿（doc-2 §6.10），v0 多源接入平面的对外接口命名为 FinDataHub：将公开类 DataHub 更名为 FinDataHub，保留 DataHub 兼容别名并标注弃用；同步 README、doc-1 与测试；行为不变。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 FinDataHub 为公开类名并从包根导出；DataHub 别名可用且标注弃用
- [x] #2 README/doc-1 同步命名与分层说明
- [x] #3 全量测试通过，行为不变
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. facade.py：DataHub → FinDataHub（类名/docstring/from_config），文件末尾 DataHub 兼容别名并标注弃用；2. __init__.py 导出两者；3. README/doc-1 命名同步；4. 测试：test_facade/test_factory 改用 FinDataHub，test_scaffold 增加别名断言；5. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：全库 164 passed；ruff/mypy 全过。实现：facade.py 类更名 FinDataHub（from_config 返回类型同步），文件末尾 DataHub = FinDataHub 兼容别名；包根同时导出；README/doc-1 命名同步；test_scaffold 增加别名断言，test_facade/test_factory 改用主名。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成对外门面更名：FinDataHub 为公开类名，DataHub 保留兼容别名并标注弃用；文档与测试同步。验证：164 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
