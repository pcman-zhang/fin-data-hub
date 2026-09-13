---
id: TASK-2.26
title: 参考数据扩展：get_security_info + etf_list/delist_list
status: Done
assignee: []
created_date: '2026-09-13 11:29'
updated_date: '2026-09-13 11:34'
labels: []
dependencies:
  - TASK-2.18
parent_task_id: TASK-2
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
① 新增 get_security_info(codes)：按代码返回标的基础信息（stock/fund/etf/index），含 list_status/list_date/delist_date 等；② get_reference 新增 kind：etf_list（对照 Tushare etf_basic：index_code/index_name/mgr_name/custod_name/mgt_fee/etf_type）、delist_list（stock_basic list_status=D）。canonical schema 增补 doc-6；Tushare spec TOML + 测试 + 文档。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 get_security_info 输出统一 schema（code/name/sec_type/list_status/list_date/delist_date/market/currency 等）
- [x] #2 etf_list 与 delist_list 纳入 get_reference（REFERENCE_COLUMNS + spec + 测试）
- [x] #3 doc-6 契约增补；全量测试与 ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. schema/枚举：SECURITY_INFO_COLUMNS、etf_list/delist_list reference 列、Capability.SECURITY_INFO；2. Tushare 适配器：fetch_security_info（stock_basic/fund_basic/index_basic 分组）+ fetch_reference 增 etf_list（etf_basic）/delist_list（stock_basic status=D）；3. BaseAdapter + capabilities 表；4. facade.get_security_info；5. 测试（adapter+facade）+ doc-6 契约增补 + README；6. 全量测试/ruff/mypy。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现与验证（2026-09-13）：
- get_security_info：按 sec_type 路由 stock_basic/fund_basic/index_basic；fund_basic、index_basic 不支持逗号多代码 → 逐代码调用（实测 multi=0）；统一列 code/name/sec_type/market/list_status/list_date/delist_date + currency（门面推导）。
- get_reference 新增 etf_list（etf_basic：index_code/index_name/setup_date/manager/custodian/mgt_fee/etf_type）与 delist_list（stock_basic status=D）。
- 测试：adapter 3 项 + facade schema/currency 1 项；实时冒烟——etf_list 1829 行、delist_list 339 行、get_security_info 5 类标的全部返回（stock/etf/lof/fund/index）。
- 全量 252 tests passed；ruff/mypy clean。doc-6 契约增补（方法签名/reference kinds/schema）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
新增 get_security_info（股票/ETF/LOF/场外/指数基础信息，按代码）与 reference kinds etf_list/delist_list；处理 fund_basic/index_basic 单代码限制；测试+实时冒烟通过，252 tests/ruff/mypy 全绿，doc-6 契约同步。
<!-- SECTION:FINAL_SUMMARY:END -->
