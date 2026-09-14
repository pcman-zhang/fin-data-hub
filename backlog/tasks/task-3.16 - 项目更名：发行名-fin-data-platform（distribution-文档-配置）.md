---
id: TASK-3.16
title: 项目更名：发行名 fin-data-platform（distribution/文档/配置）
status: In Progress
assignee: []
created_date: '2026-09-14 06:46'
updated_date: '2026-09-14 06:46'
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
- [ ] #1 pyproject name/description 更新；动态版本仍取 fin_data_hub._version（单一来源）
- [ ] #2 README 安装示例/版本说明、AGENTS 标题、backlog project_name 更新
- [ ] #3 editable 安装验证 + 全量测试/ruff/mypy 通过
<!-- AC:END -->
