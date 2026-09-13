---
id: doc-3
title: Fuyao REST API 接入参考（开发用）
type: specification
created_date: '2026-09-13 09:03'
updated_date: '2026-09-13 09:56'
---
# Fuyao REST API 接入参考（开发用）

> 用途：fin-data-hub 接入 Fuyao（同花顺金融数据API）REST 的离线开发参考（一期）。
> 权威文档：https://fuyao.aicubes.cn/docs/api-reference/overview/ ；完整聚合：https://fuyao.aicubes.cn/llms-full.txt
> 状态：当前免费、不限累计调用次数；服务按负载动态限流（HTTP 429 或 `code=4001`）。

## 1. 通用约定

- **Base URL**：`https://fuyao.aicubes.cn`
- **鉴权**：请求头 `X-api-key: <api-key>`；缺失/无效返回 `code=2001`；无权限 `code=2003`
- **响应信封**：
  ```json
  {"code": 0, "message": "success", "request_id": "...", "data": {"timestamp": 1716105600000, "item": []}}
  ```
  业务结果由 `code` 表达（HTTP 恒 200；限流可能 429）；`request_id` 用于排障
- **时间戳**：毫秒级 Unix 时间戳；时区 `Asia/Shanghai`
- **代码**：完整 `thscode`（如 `600519.SH`）；**不接受纯代码**；场外基金 `.OF` 不是交易所
- **币种/单位**：A 股价格与成交额为原始货币（CNY）、成交量单位为**股**

### 错误码

| code | 含义 | 对应 hub 异常 |
|---|---|---|
| 0 | 成功 | — |
| 1001/1002/1003/1004 | 缺参/格式/越界/冲突 | `ValueError` |
| 2001 | 未认证 | `MissingCredentialError` |
| 2003 | 权限不足 | `UnsupportedCapability` |
| 3001/3002/3004 | 标的不存在/未就绪/类型不支持 | `SourceError` |
| 4001（或 HTTP 429） | 限流 | `RateLimitError`（退避重试） |
| 5001/5002/5003 | 服务端错误/上游超时/数据源不可用 | `SourceError`（5002/5003 可重试） |

## 2. 一期端点规格（对应 TASK-2.16）

### 2.1 行情快照 `GET /api/a-share/prices/snapshot`

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `thscodes` | string | 否 | 逗号分隔 thscode 批量；给定则忽略分页 |
| `limit` | int | 否 | 分页大小（默认 100，仅在省略 thscodes 时） |
| `offset` | int | 否 | 分页偏移（默认 0） |

响应 `item[]`：`thscode`、`ticker`、`last_price`、`price_change`、`price_change_ratio_pct`、`open_price`、`high_price`、`low_price`、`prev_price`、`volume`（股）、`turnover`（元）；不返回中文名。

**归一化**（→ `SNAPSHOT_COLUMNS`）：

| canonical | 来源 |
|---|---|
| `code` | `thscode` |
| `date` | ⚠️ 无交易日期字段，需由 `data.timestamp`（Asia/Shanghai）推导或结合日历 |
| `last/open/high/low/prev_close` | `last_price/open_price/high_price/low_price/prev_price` |
| `volume` / `amount` | `volume`（股）/ `turnover`（元） |

### 2.2 历史 K 线 `GET /api/a-share/prices/historical`

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `thscode` | string | 是 | **单标的，不接受逗号** |
| `interval` | string | 是 | 当前仅支持 `1d` |
| `start` / `end` | long | 是 | 毫秒时间戳；**窗口跨度 ≤ 10 年**，超限 `code=1003` |
| `adjust` | string | 否 | `none` / `forward` / `backward`（默认 `forward`） |

响应 `item[]`：`date_ms`、`open_price`、`high_price`、`low_price`、`close_price`、`volume`（股）、`turnover`（元）。

**归一化**（→ `BARS_COLUMNS`）：`date_ms` → `datetime64[ns]`；`adjust` 映射 `None→none / qfq→forward / hfq→backward`；单位已一致（股/元）。

**约束**：多标的需逐次请求（capability `max_codes_per_call=1`）；**超过 10 年的区间需按窗口分块并合并**。

### 2.3 标的检索 `GET /api/meta/tickers/search`

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `q` | string | 是 | thscode / ticker / 中英文名（子串匹配） |
| `exchange` | string | 否 | `SH`/`SZ`/`BJ` 或期货交易所代码 |
| `asset_type` | string | 否 | `a-share`、`a-share-index`、`fund-otc`、`fund-etf`、`fund-lof`、`fund-reits`、`forex`、`futures`、`options` |
| `limit` | int | 否 | 最大 50（默认 10） |

响应 `item[]`：`thscode`、`ticker`、`name`、`exchange`、`asset_type`、`currency`、`list_date`、`end_date`、`last_trade_date`、`last_delivery_date`。

### 2.4 标的列表 `GET /api/meta/tickers/list`

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `asset_type` | string | 否 | 同上，可逗号多值；省略返回全部 |
| `limit` | int | 否 | 最大 10000（默认 1000） |
| `offset` | int | 否 | 分页偏移（循环至 `item.length < limit` 取尽） |

响应字段同 2.3。**归一化**（→ `REFERENCE_COLUMNS`）：

| canonical | 来源 |
|---|---|
| `code` / `name` / `list_date` | `thscode` / `name` / `list_date` |
| `market` | `exchange`（场外基金为 null） |
| `industry` | ⚠️ 接口不提供，置空 |

### 2.5 交易日历 `GET /api/a-share/calendar/trading-days`

无入参；固定窗口 `[今日 - 1 年, 今日]`（Asia/Shanghai）。响应 `item[]`：`date_ms`、`date`（`yyyyMMdd`）。

**归一化**（→ `CALENDAR_COLUMNS`）：列表内日期 `is_open=true`；请求区间内的非列表日按 `is_open=false` 补齐（与 AkShare 适配器一致）。⚠️ 超出固定窗口的请求需回退其他源或报错。

## 3. 后续端点目录（未接入）

| 分组 | 路径前缀 | 状态 |
|---|---|---|
| 估值数据 | `/api/a-share/valuations` | 可用（多股票最新估值快照） |
| 财务数据 | `/api/a-share/financials` | 可用（三大报表多期序列） |
| 财务指标 | `/api/a-share/financials/indicators` | 可用（成长/盈利/偿债/营运/现金流） |
| 除复权 | `/api/a-share/corporate-actions` | 可用（复权因子事件流） |
| 主力资金 | `/api/a-share/capital-flow` | 可用 |
| 高频动向 | `/api/a-share/high-frequency` | 可用 |
| 集合竞价 | `/api/a-share/auction` | 可用 |
| 特色数据 | `/api/a-share/special-data` | 可用（涨跌停/热榜/异动/龙虎榜） |
| 同花顺指数 | `/api/a-share-index` | 可用（列表/成分/行情） |
| 全市场导出 | `/api/dump/market-dumps` | 可用（Parquet：10 年日 K、近 10 日、复权因子） |
| 基金 | `/api/fund/**` | 可用（资料/持仓/业绩/经理/财务/资讯等） |
| 期货 | `/api/futures/**` | 可用（资料/持仓/仓单/基差/行情） |
| 期权 | `/api/options/**` | 可用（资料/行情/会话） |
| 股票基础信息 | `/api/a-share/stock-basics` | 敬请期待 |
| 个股所属指数 | `/api/a-share/ths-index-membership` | 敬请期待 |
| 指数概况/成分权重 | `/api/a-share-index`（部分） | 敬请期待 |

## 4. 开发注意事项

1. **能力映射**：snapshot → `snapshot`；historical → `bars`（单标的 + 10 年分块）；tickers/* → `reference`；calendar → `trade_calendar`
2. **限流**：默认 2 QPS（可覆盖）；4001/429 走退避重试
3. **凭证**：`FuyaoConfig(api_key)` 注入；集成测试用 `FIN_DATA_HUB_FUYAO_API_KEY`
4. **快照缺交易日期**：canonical `date` 需由 `data.timestamp` 推导（注意时区）或结合交易日历
5. **分页**：snapshot/list 循环 offset；search 上限 50
6. **免费期**：当前不限累计次数，但需控制频率（动态限流）
7. **归一化层**：本参考的字段映射将作为 TASK-2.18 映射 spec 的输入

## 5. 复权数据口径与对账结论（2026-09-13 实测）

**接口行为**：

- `historical` 的 `adjust=forward|backward` 返回**预计算复权价**（非因子）。
- `corporate-actions/adjustment-factors` 返回**原始公司行为事件**（`ex_date_ms`、`dividend_per_share`、`per_share_bonus`），不含因子，需自行推导；每次请求仅一个 thscode。

**对账实验（600519.SH，2024-01-01 ~ 2026-09-11，654 个交易日）**：

| 检查项 | 结果 |
|---|---|
| 原始收盘价（Tushare vs Fuyao `adjust=none`） | **完全一致**（最大差 0.0） |
| Tushare `adj_factor` 事件乘数 vs 理论 `P_prev/(P_prev−D)` | 一致（2026-06-26：1.023667 vs 1.023668，仅舍入差） |
| Fuyao `backward` ÷ (raw × Tushare adj_factor) | **非常数**：0.789~0.829（累计偏差约 27%） |
| Fuyao 同日 OHLC 的 `bwd/raw` 比值 | **各字段不一致**（如 2024-09-24：open 6.578 / high 6.517 / low 6.593 / close 6.517） |
| Fuyao `bwd` 内部 `close/open` vs raw 内部 | **被改变**（1.068096 → 1.058260） |
| Fuyao 隐含因子日常波动 | 普通交易日亦波动，且与当日涨跌幅反向（疑似基于均价等非收盘基准） |
| Fuyao 事件乘数 vs 理论 | 不一致（2026-06-26：1.02656 vs 1.02367） |

**结论**：

1. Fuyao 的预计算复权价**不符合"原始价 × 统一累计因子"的标准语义**，**不可作为复权对账基准**。
2. 平台复权口径以 **原始价 + 因子**为准（Tushare `adj_factor` 与理论一致，已验证）。
3. Fuyao 的事件流可用于推导因子，但推导结果须**逐事件与 Tushare 对账**后使用。
4. 建议向 Fuyao 反馈该数据质量问题（同日 OHLC 复权比值不一致）。
5. **Hub 处置（v0）**：FuyaoAdapter 仅支持 `adjust=None`；`qfq/hfq` 抛 `UnsupportedCapability` 并提示改用 Tushare/Wind 或原始价 + 因子（TASK-2.20）。
