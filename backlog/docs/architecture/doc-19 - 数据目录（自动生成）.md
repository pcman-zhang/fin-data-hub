---
id: doc-19
title: 数据目录（自动生成）
type: specification
created_date: '2026-09-13 14:44'
updated_date: '2026-09-14 08:18'
---
# 数据目录（自动生成）

> 回答两个基础问题：**我们有哪些数据**、**以什么 code / 方式获取**（doc-18 §5）；
> 随数据字典更新重新生成，请勿手改。

| dataset | 域 | 说明 | 实体 | PIT 类别 | 来源 | 获取方式 |
|---|---|---|---|---|---|---|
| `cn_equity.adj_factor` | cn_equity | 复权因子（累计后复权口径；事件步进，按知识时间版本化） | entity | market | baostock, tushare | `get_adjust_factors` |
| `cn_equity.daily_bar` | cn_equity | A 股日线行情（不复权原始价；复权价按 raw + factor、as-of 计算） | entity | market | baostock, tushare | `get_bars(adjust=None/qfq/hfq)` |
| `cn_equity.financials.balance_sheet` | cn_equity | 资产负债表（核心列；append-only 版本，按公告日知识时间；以 issuer_id 为键） | entity | versioned | tushare | `get_financials(kind="balance_sheet")` |
| `cn_equity.index_member` | cn_equity | 申万行业成分（三级；区间型 PIT，含已剔除记录） | entity | scd2 | tushare | `get_reference("industry_member")` |
| `cn_equity.index_weight` | cn_equity | 指数成分与权重（月度快照；快照型 PIT，as-of 取最近一期） | entity | snapshot | tushare | `get_index_weights` |
| `cn_equity.listing_lifecycle` | cn_equity | 交易状态（上市/暂停/退市）；PIT Universe 权威来源，替代注册表交易状态 | entity | scd2 | tushare | `get_reference("stock_list") / 内部` |
| `cn_equity.market_events.namechange` | cn_equity | 名称变更历史（生效闭区间 + 公告日；用于 as-of 属性还原） | entity | scd2 | tushare | `get_market_events(kind="namechange")` |
| `cn_fund.nav` | cn_fund | 场外基金净值（单位净值/累计净值；日频） | entity | market | akshare, tushare | `get_fund_nav` |
| `ref.entity` | ref | 引用注册表（实体身份 + 分类面 + PIT 属性；SCD2；issuer/listing/series/basket） | entity | scd2 | — | `get_security_info / 内部` |
| `ref.entity_code_history` | ref | canonical 代码履历（代码变更/复用 → 旧码仍可解析；替代多源别名表） | entity | scd2 | — | `内部（Hub mapper）` |
| `ref.entity_external_id` | ref | 实体外部标识（isin/figi/cusip/sedol/lei/uscc；不含 ticker） | entity | scd2 | — | `内部（外部标识注册）` |
| `ref.entity_relation` | ref | 实体关系（单向存储；双向查询由 relation_type_dict.inverse_relation 驱动） | entity | scd2 | — | `内部（关系注册）` |
| `ref.relation_type_dict` | ref | 关系词表（新增关系词必须先登记；双向查询由 inverse_relation 驱动） | none | scd2 | — | `内部（关系词表）` |
