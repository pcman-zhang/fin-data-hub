---
id: TASK-2.1
title: 脚手架：打包配置 + 目录结构 + 错误类型
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:03'
labels: []
dependencies: []
parent_task_id: TASK-2
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
建立标准 src 布局与 pyproject.toml；核心依赖 pandas>=3.0；可选 extras tushare/akshare/ifind/wind/dev；定义 Source 枚举与错误体系。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 pyproject.toml 声明核心依赖与 extras；python3 -m pip install -e .[dev] 成功
- [x] #2 src/fin_data_hub 可 import；版本号可读取
- [x] #3 errors.py 定义 MissingCredentialError/UnsupportedCapability/RateLimitTimeout/RateLimitError/UnknownSecurityError
- [x] #4 pytest 与 ruff 配置就位，pytest 空跑通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 编写 pyproject.toml（src 布局、pandas>=3.0、extras: tushare/akshare/ifind/wind/dev、pytest/ruff 配置）；2. 建 src/fin_data_hub：__init__/_version/enums/errors/py.typed；3. .gitignore；4. 创建 .venv 并 pip install -e ".[dev]"；5. 运行 pytest 与 ruff 验证；6. 记录验证结果并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：.venv 创建成功；pip install -e .[dev] 成功；pytest 5 passed；ruff check 全过。pyproject 采用动态版本（读取 fin_data_hub._version），extras: tushare/akshare/ifind/wind/dev；pytest markers 含 integration。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成脚手架：pyproject.toml（src 布局、pandas>=3.0、extras、pytest/ruff/mypy 配置）、src/fin_data_hub（__init__/_version/enums/errors/py.typed）、.gitignore、tests/test_scaffold.py。验证：pip install -e .[dev] 成功，pytest 5 passed，ruff 全过。
<!-- SECTION:FINAL_SUMMARY:END -->
