---
id: doc-8
title: 复权数据对账说明（Reconciliation Guide）
type: guide
created_date: '2026-09-13 11:01'
updated_date: '2026-09-13 11:03'
---
# 复权数据对账说明（Reconciliation Guide）

> 状态：维护中 | 关联报告：R1 = `doc-4`、R2 = `doc-9` | 相关设计：doc-2 §6.16、doc-5（Router Policy）、doc-7（BaoStock 参考）

## 1. 目的

统一说明**复权数据口径对账**的方法与结论，作为 Router `factor_source` 选择、数据入库与质量检查的依据。所有对账实验以**报告**形式留档，本说明只维护方法与结论索引。

## 2. 对账方法（统一口径）

**基准**：Tushare（`daily` + `adj_factor`），已验证其事件乘数与理论一致（doc-4）。
**公式**：
- 事件理论乘数：`m = P_prev × (1 + B) / (P_prev − D)`（D=每股分红，B=每股送股，P_prev=除权前收盘）
- 归一化因子：`f_norm = f / f_last`
- 事件实测乘数：`m = (X_after / X_before) / (raw_after / raw_before)`
- 自洽性（源自身）：`qfq ≈ raw × f / f_last`；`hfq ≈ raw × f`（含源锚点）

**步骤（SOP）**：
1. 原始价一致性（两源 raw 收盘最大差应 ≈ 0）；
2. 因子归一化比较（`f_norm` 比值应为常数 ≈ 1；std 应 ≤ 1e-4 量级）；
3. 逐事件乘数对照（与基准/理论，ppm 级差异可接受）；
4. 源自身复权价与 `raw × 因子` 自洽性；
5. 记录限制（锚点差异、舍入、覆盖窗口、频率）。

## 3. 报告索引与结论

| 报告 | 对象 | 结论 | 处置 |
|---|---|---|---|
| R1（`doc-4`） | Fuyao `historical(adjust=forward/backward)` | **不通过**：同日 OHLC 复权比值不一致、日收益衰减 0.844×、非除权日因子波动 | 禁用 Fuyao 原生复权（TASK-2.20）；复权由 Router 组合 raw+factor |
| R2（`doc-9`） | BaoStock `query_adjust_factor` + 自有复权价 | **通过**：原始价一致；归一化因子与 Tushare 一致（std 6.5e-06）；事件乘数差 ≤ 4.6 ppm；`qfq = raw × f/f_last` 自洽（比值 1.000000） | 可作为 Router `factor_source`（免费，可选；默认仍 Tushare） |

## 3.1 复权因子覆盖矩阵（实测 2026-09-13）

| 资产类型 | Tushare `adj_factor` | Tushare `fund_adj` | BaoStock `query_adjust_factor` | 备注 |
|---|---|---|---|---|
| 股票 | ✅ 654 行 | — | ✅（R2 通过） | |
| ETF | ❌ 空 | ✅ 654 行（510300.SH 最新 1.2671） | ❌ 空 | Tushare 需走 `fund_adj` |
| LOF | ❌ 空 | ✅ 654 行（161725.SZ 最新 1.0645） | ❌ 空 | 同上 |
| 场外基金 | ❌ 空 | ❌ 空 | — | 用净值/分红口径，暂无因子 |
| 指数 | ❌ 空 | ❌ 空 | ❌ 空 | 价格指数无需复权 |

**结论**：Tushare 因子通道需**按资产类型选择接口**（股票 `adj_factor`；ETF/LOF `fund_adj`）；BaoStock 因子仅覆盖股票。

## 4. 结论对 Router 的影响

- `RoutingConfig.factor_source`：默认 `TUSHARE`（股票走 `adj_factor`、ETF/LOF 走 `fund_adj`，见 §3.1 矩阵）；`BAOSTOCK` 仅适用于股票；
- 因子不可用的组合（如 ETF + factor_source=baostock、场外基金调整）应**明确报错**（`UnsupportedCapability`），不得静默回退；
- `trusted_native_adjust`：当前 `{TUSHARE, AKSHARE}`（Wind/iFinD 开发期排除，见 doc-5）；
- **hfq 锚点差异**：各源累计因子锚点不同（BaoStock ≈ Tushare × 0.887），跨源 hfq **不可直接比较**；每个数据平面/存储固定单一 `factor_source`；
- 新增因子源必须完成本 SOP 并在本说明登记。

## 5. 报告模板要点

每份报告需包含：① 标的与数据范围；② 数据源与接口；③ 计算公式与参数；④ 结果（raw 一致性、因子归一化、事件乘数对照、自洽性）；⑤ 限制与结论；⑥ 复现步骤（不含凭证）。
