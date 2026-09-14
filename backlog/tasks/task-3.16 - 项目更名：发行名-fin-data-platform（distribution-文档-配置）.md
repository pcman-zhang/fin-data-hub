---
id: TASK-3.16
title: 项目更名：发行名 fin-data-platform（distribution/文档/配置）
status: Done
assignee: []
created_date: '2026-09-14 06:46'
updated_date: '2026-09-14 08:07'
labels: []
dependencies: []
parent_task_id: TASK-3
ordinal: 51000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub 仓库已更名 fin-data-platform；同步发行包名与文档：pyproject name、README 安装示例、AGENTS 标题、backlog project_name。模块名 fin_data_hub（接入层）/ fin_data_platform（平台层）保持不变。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 pyproject name/description 更新；动态版本仍取 fin_data_hub._version（单一来源）
- [x] #2 README 安装示例/版本说明、AGENTS 标题、backlog project_name 更新
- [x] #3 editable 安装验证 + 全量测试/ruff/mypy 通过
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
目录改名后复验（新路径 editable 重装）：pip install -e . → fin-data-platform 0.0.1；pytest 307 passed（8 deselected 为默认跳过的集成测试）；ruff check 全通过；mypy 52 文件无问题。pyproject 动态版本仍取 fin_data_hub._version（单一来源）；README 安装示例、AGENTS 标题、backlog project_name 均已更新为 fin-data-platform。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
发行名 fin-data-hub → fin-data-platform：更新 pyproject name/description、README 安装示例与版本说明、AGENTS 标题、backlog project_name；模块名 fin_data_hub（接入层）/ fin_data_platform（平台层）保持不变。验证：editable 安装 + 307 测试 + ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
