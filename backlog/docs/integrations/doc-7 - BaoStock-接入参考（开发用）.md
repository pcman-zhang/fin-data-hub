---
id: doc-7
title: BaoStock 接入参考（开发用）
type: guide
created_date: '2026-09-13 10:58'
updated_date: '2026-09-13 11:08'
---
# BaoStock 接入参考（开发用）

> 用途：fin-data-hub 接入 BaoStock（免费源）的开发参考。官方文档：https://www.baostock.com/mainContent?file=home.md
> 文档获取方式（SPA，静态抓不到正文）：`POST /helpdocs/api/markdown/<file>`；菜单：`POST /helpdocs/api/menu`。

## 1. 文档页面清单（菜单 32 页，节选）

| 页面 | 内容 |
|---|---|
| `stockKData.md` | A 股 K 线（日/周/月/5-60 分钟） |
| `factorInfo.md` | **复权因子（query_adjust_factor）** |
| `dataExplain.md` | 数据格式说明、退市/停牌、总股本、复权因子简介、指数清单 |
| `indexData.md` | 指数数据 |
| `stockBasic.md` / `StockBasicInfoAPI.md` | 证券基本资料/元信息 |
| `dividInfo.md` | 除权除息信息 |
| `seasonProfit/Operation/Growth/Balance/CashFlow/Dupont/Express/Forecast.md` | 季频财务 |
| `stockIndustry.md` | 行业分类 |
| `sz50Stock / hs300Stock / zz500Stock.md` | 指数成分 |
| `depositRate / loanRate / reserveRatio / supplyData / supplyDataYear.md` | 宏观利率/货币 |
| `default.md` | 访问规则（旧 wiki 内容） |
| `modifyRecord.md` | 数据调整记录 |

## 2. 关键接口要点

### 2.1 K 线 `query_history_k_data_plus`

- 代码：`sh.600000` / `sz.000001`（仅 SH/SZ；分钟线不含指数）；
- 频率：`d` / `w` / `m` / `5` / `15` / `30` / `60`；
- 复权：`adjustflag` = 1 后复权 / 2 前复权 / 3 不复权；
- 字段（日线示例）：`date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST`；
- 周/月线字段：`date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg`；
- 分钟线字段：`date,time,code,open,high,low,close,volume,amount,adjustflag`；
- 覆盖：1990-12-19 至今。

### 2.2 复权因子 `query_adjust_factor`（重要）

- 参数：`code`（不可为空）、`start_date`（默认 2015-01-01）、`end_date`（默认今天）；
- 字段：`code / dividOperateDate / foreAdjustFactor / backAdjustFactor / adjustFactor`；
- 文档口径：**BaoStock 提供的是"涨跌幅复权算法"因子**（不是价格比例复权的直接因子）；
  - `foreAdjustFactor` = 除权除息日前一交易日收盘价 / 除权日最近一个交易日的前收盘价；
  - `backAdjustFactor` = 除权日最近一个交易日的前收盘价 / 除权除息日前一交易日收盘价；
  - `adjustFactor` = 本次复权因子；
- 实测（sh.600000）：2024-07-18 → back 12.388310；2025-07-16 → back 12.763991（呈累计特征）。
- **覆盖范围（实测 2026-09-13）**：仅**股票**（`sh.510300`/`sz.161725`/`sh.000300` 均为空）；ETF/LOF/指数无因子。

### 2.3 其他

- `query_stock_basic`（证券基本资料）、`query_trade_dates`（交易日历）、`query_all_stock`（某日全市场）、指数/成分/财务/行业等见页面清单。

### 2.4 因子通道实现（2026-09-13 起）

- `BaoStockAdapter.fetch_adjust_factors`：每次**仅一个代码**（Registry 上限 1，门面自动分块）；
- 查询固定从 `1990-01-01` 回看，输出 = **窗口基准行**（`start` 处，取最近历史事件的累计因子；无历史事件则为 1.0）+ **窗口内事件行**（`dividOperateDate` + `backAdjustFactor`）；
- 因子为累计后复权因子（事件步进语义），Router `apply_adjustment` 用 backward `merge_asof` 对齐，支持非交易日 `start`；`qfq = raw×f/f_last`、`hfq = raw×f`；
- 仅覆盖**股票**（ETF/LOF/指数为空，实测）；非股票代码显式抛 `UnsupportedCapability`；
- 对账：R2（doc-9）通过；与 Tushare 的差异仅锚点常数（hfq）与 ppm 级舍入。

## 3. 口径警告与后续（必须）

1. **涨跌幅复权 ≠ 价格比例复权**：BaoStock 因子/复权价与 Tushare `adj_factor` 口径可能不同；
   在作为 Router `factor_source` 之前，必须按 doc-4 的方法做**对账验证**（同一标的、重叠期，
   比较 `raw × factor` 与两源复权价；逐事件乘数对照理论 `P_prev(1+B)/(P_prev−D)`）。
2. 适配器现状（TASK-2.22）：bars / reference(stock_list) / trade_calendar 已实现；
   **未实现** `query_adjust_factor` 通道、周/月/分钟频率、指数、财务/行业/成分等。
3. 文档获取方式可作为开发期参考手段，但**不要把外部文档正文批量复制进仓库**；只保留自洽结论与映射。
