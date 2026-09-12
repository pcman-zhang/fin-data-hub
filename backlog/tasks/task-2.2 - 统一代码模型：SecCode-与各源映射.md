---
id: TASK-2.2
title: 统一代码模型：SecCode 与各源映射
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:04'
labels: []
dependencies:
  - TASK-2.1
parent_task_id: TASK-2
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
SecCode 值对象（symbol.VENUE 解析/格式化/校验/类型推断）+ 各源代码映射：Tushare/Wind/iFinD 直通，AkShare 按 endpoint 转 6 位或专有格式；规则表驱动。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 解析 600000.SH/000001.SZ/920002.BJ/510300.SH/159915.SZ/000001.OF/000300.SH/399006.SZ 全部通过
- [x] #2 非法输入抛 UnknownSecurityError；裸代码与小写 venue 行为有测试
- [x] #3 AkShare 映射按 endpoint 返回正确参数形式
- [x] #4 单测覆盖 000001.SZ 与 000001.OF 歧义及类型推断
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. codes.py：SecType 枚举、SecCode 值对象（解析/格式化/校验/类型推断，含 venue 规则与 CN 六位补零）；2. mapping.py：BaseMapper + 直通 mapper（Tushare/Wind/iFinD）+ AkShareMapper（按 endpoint 的代码形式）；3. tests/test_codes.py 与 tests/test_mapping.py 覆盖 AC 场景；4. 运行 pytest + ruff；5. 记录验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_codes.py + tests/test_mapping.py 共 34 passed；ruff 与 mypy 全过。实现含 CN venue 规则（SH 5/6/000/950、SZ 00/30/15/16/39、BJ 4/8/9、OF）、预留 venue 需显式 sec_type、1-6 位数字自动补零、AkShare 指数 endpoint 分 plain/prefixed。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成统一代码模型：SecCode/SecType/parse_codes（codes.py）与 CodeMapper（mapping.py，Tushare/Wind/iFinD 直通 + AkShare 按 endpoint）。验证：34 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
