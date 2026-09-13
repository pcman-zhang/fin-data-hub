---
id: doc-6
title: 归一化层与 FinDataHub API 契约设计
type: specification
created_date: '2026-09-13 10:28'
updated_date: '2026-09-13 11:38'
---
# 归一化层与 FinDataHub API 契约设计

> 状态：设计稿（待确认） | 关联：doc-1（v0 架构）、doc-5（Router 策略）、TASK-2.18

## 1. 设计顺序

先**冻结 FinDataHub API 签名与 canonical schema**（输出契约），再设计两层归一化：
- **1.1 请求侧映射**：canonical（WindCode）→ 具体 adapter 调用参数；
- **1.2 响应侧归一化**：adapter 原始返回 → canonical 输出。

没有输出契约，响应归一化就没有目标；因此契约先行。

## 2. FinDataHub API 契约（v0）

### 2.1 公共方法签名

```python
class FinDataHub:
    # —— 已实现 ——
    def get_bars(codes, *, start, end, freq="1d", adjust=None, source=None,
                 fields=None, force=False, ttl=None) -> pd.DataFrame
    def get_snapshot(codes, *, fields=None, source=None, force=False, ttl=None) -> pd.DataFrame
    def get_fund_nav(codes, *, start=None, end=None, source=None, force=False, ttl=None) -> pd.DataFrame
    def get_reference(kind, *, source=None, force=False, ttl=None) -> pd.DataFrame
    def get_security_info(codes, *, source=None, force=False, ttl=None) -> pd.DataFrame
    def get_trade_calendar(*, start, end, source=None, force=False, ttl=None) -> pd.DataFrame
    def stats() -> dict

    # —— 已纳入冻结契约（平台 raw+factor 管线） ——
    def get_adjust_factors(codes, *, start, end, source=None, force=False, ttl=None) -> pd.DataFrame
    def get_adjustment_events(codes, *, start=None, end=None, source=None, force=False, ttl=None) -> pd.DataFrame

    # —— 预留接口（v0 调用即抛 UnsupportedCapability，签名先冻结） ——
    def get_intraday_bars(codes, *, start, end, freq="1m", source=None,
                          fields=None, force=False, ttl=None) -> pd.DataFrame
    def get_edb_series(indicators, *, start, end, source=None, force=False, ttl=None) -> pd.DataFrame
```

### 2.1a `get_bars` 与 `get_snapshot` 的区别

| | `get_bars` | `get_snapshot` |
|---|---|---|
| 数据形态 | **历史时间序列**（K 线，逐日/逐周期） | **当前时点截面**（最新状态） |
| 主键 | `code + date` | `code`（`date` 为快照时点） |
| 参数 | 必填 `start/end`、`freq`、`adjust` | 无区间参数 |
| 用途 | 回测、序列分析、复权 | 当前价/盘口/当日状态、选股筛选 |
| 源支持 | 全部源 | Wind、Fuyao（AkShare/Tushare 暂无稳定快照） |
| 缓存 TTL | 付费源 6h；收盘后至下一交易日 | 短（30–60s） |

### 2.1b 预留接口行为

- `get_intraday_bars`：高频透传特性（doc-2 §6.15，暂不开发）→ 调用抛 `UnsupportedCapability`，消息注明"预留接口，见 doc-2 §6.15"；
- `get_edb_series`：宏观数据平面后续接入 → 调用抛 `UnsupportedCapability`，消息注明"预留接口，宏观平面规划中"；
- 签名冻结的意义：外部代码可按最终形态编码，实现就绪时无需破坏性升级。

约定：
- `codes`：`str | SecCode | Sequence[str | SecCode]`，均为 canonical WindCode；
- 日期参数：`YYYYMMDD` 或 `YYYY-MM-DD`；
- `adjust`：`None | "qfq" | "hfq"`（路由见 doc-5）；
- `source`：`Source | str | None`（None 时用 `HubConfig.default_source`，否则报错）；
- `fields`：canonical 字段白名单（None = 全部规范列）；
- `force`/`ttl`：缓存控制。

### 2.2 canonical schema（列名 / 类型 / 单位 / 语义）

| endpoint | 列 | 类型 | 单位/语义 |
|---|---|---|---|
| bars | `code` | str | canonical `symbol.VENUE` |
| | `date` | datetime64[ns] | 日线日期（Asia/Shanghai，tz-naive，归一化到 00:00） |
| | `open/high/low/close` | float64 | 原始货币（CNY） |
| | `volume` | float64 | **股** |
| | `amount` | float64 | **原始货币元** |
| | `currency` | str | ISO 4217（由 venue 推导，见 §2.2a） |
| snapshot | `code/date/last/open/high/low/prev_close` | 同上 | 快照时点日期与价格 |
| | `volume/amount` | float64 | 股 / 元 |
| | `currency` | str | ISO 4217（由 venue 推导） |
| fund_nav | `code/date/unit_nav/accum_nav` | float64 | 元（`currency` 列标注） |
| | `daily_return` | float64 | **百分比数值**（1.23 = +1.23%） |
| reference(stock_list) | `code/name/list_date/market/industry` | str/datetime64/str | market ∈ SH/SZ/BJ；缺失为 None |
| reference(fund_list) | `code/name/fund_type/management/list_date/market` | 同上 | |
| reference(etf_list) | `code/name/fullname/index_code/index_name/setup_date/list_date/list_status/exchange/manager/custodian/mgt_fee/etf_type` | str/datetime64/float | 对照源 etf 基础信息 |
| reference(delist_list) | `code/name/list_date/delist_date/market` | str/datetime64 | 退市标的列表 |
| reference(industry_classify) | `index_code/name/level/industry_code/parent_code/is_pub/src` | str | 申万三级树；`parent_code` 引用上级 `industry_code` |
| reference(industry_member) | `code/name/l1_code/l1_name/l2_code/l2_name/l3_code/l3_name/in_date/out_date/is_new` | str/datetime64 | 区间型 PIT（保留已剔除记录） |
| reference(index_list) | `code/name/market/category/publisher/list_date` | 同上 | |
| security_info | `code/name/sec_type/market/list_status/list_date/delist_date` | str/datetime64 | 按代码基础信息（股票/ETF/LOF/场外/指数） |
| trade_calendar | `date/is_open` | datetime64[ns]/bool | 区间内逐日 |
| adjust_factors（adapter 级） | `code/date/adj_factor` | float64 | 绝对累计因子（统一锚点，当前 Tushare） |
| adjustment_events（adapter 级） | `code/ex_date/dividend_per_share/per_share_bonus` | float64 | 每股、税前 |

### 2.2a 货币口径（currency）

- 所有涉及金额/价格的输出**新增 `currency` 列**（ISO 4217），由 canonical venue 集中推导（归一化层职责，不依赖各源返回）：

| venue | currency |
|---|---|
| `.SH` / `.SZ` / `.BJ` / `.OF` / `.TI` / `.WI` | CNY |
| `.HK` | HKD |
| `.O` / `.N` / `.A` | USD |
| `.GI` | 需参考数据判定（如 SPX→USD、HSI→HKD、DAX→EUR）；无法判定时为 `None` |
| `.CSI` | CNY |

- 跨市场混合请求：逐行 `currency` 保证正确；v0 实际以 CN 为主。
- `get_reference` 返回的 `currency` 用于主数据（Fuyao TickerItem 已含）。
- 汇率域（USDCNY 等）属宏观平面（预留），不在行情 schema 内。

### 2.3 attrs 契约

`df.attrs`：`source`（实际主数据源）、`requested_source`、`factor_source?`、`filled_from?`、`adjust?`、`cached`、`fetched_at`（ISO8601 UTC）、`code_format="canonical"`。

## 3. 1.1 请求侧映射（WindCode → adapter 调用）

### 3.1 canonical venue（Wind 标准）

`.SH / .SZ / .BJ / .OF / .CSI / .HK / .O / .N / .A / .GI / .TI / .WI`
- `.O/.N/.A`：美股交易所；`.GI`：全球指数；`.TI`：同花顺指数；`.WI`：Wind 指数。
- 数据源不支持时**映射校准**（不改变 canonical），无法表达则 `UnsupportedCapability`。

### 3.2 映射职责

| 内容 | 说明 |
|---|---|
| 代码 | `CodeMapper.to_source(code, endpoint)`；按 source × venue/type × endpoint（如 AkShare 指数前缀、Tushare `.TI`、Fuyao thscode） |
| 代码还原 | `from_source(raw, venue=?, endpoint=?)` → canonical（用于响应归一化） |
| 参数 | 日期格式、`adjust` 枚举、`freq`、endpoint 专有参数（period/no-adjust 等） |

## 4. 1.2 响应侧归一化（adapter → canonical）

### 4.1 职责

字段映射、单位换算（手→股、千元→元等）、枚举映射、日期/时区、代码 canonical 化、必需列校验（缺失→`ResponseParseError`）。

### 4.2 Spec 驱动（机读）

目录：`src/fin_data_hub/specs/<source>.toml`（TOML，stdlib `tomllib` 读取，无新依赖）

结构（示例）：

```toml
[code]
venue_style = "passthrough"            # passthrough | strip_venue | ...
index_prefixes = { SH = "sh", SZ = "sz", CSI = "csi" }  # 按 endpoint 可覆盖

[params]
adjust = { none = "none", qfq = "forward", hfq = "backward" }
date_format = "%Y%m%d"

[response.bars]
required = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]
code = { source = "ts_code", type = "code", venue = "from_code" }
date = { source = "trade_date", type = "date", format = "%Y%m%d" }
open = { source = "open", type = "float" }
close = { source = "close", type = "float" }
volume = { source = "vol", type = "float", factor = 100 }    # 手→股
amount = { source = "amount", type = "float", factor = 1000 } # 千元→元
```

- `factor` 支持常数或命名换算（`lot_to_share`、`thousand_to_yuan`、`wan_to_yuan`）；
- `type` ∈ `code/date/float/int/str/bool`；
- 未列出的 canonical 列视为缺失 → 校验报错或置空（按 endpoint 允许可空）。

### 4.3 运行时

```python
normalize(raw: pd.DataFrame, spec: ResponseSpec, *, source: Source, endpoint: str) -> pd.DataFrame
```
- 由 adapter 调用（迁移后），或作为 CI 一致性校验（迁移期金样对照：spec 归一化结果 ≡ 现有 adapter 输出）。

### 4.4 校验（CI）

1. 覆盖度：每个 adapter 声明的 capability/endpoint 必须有对应 response spec；
2. schema 一致性：spec 的目标列 ⊆ canonical schema，必需列齐备；
3. 金样对照：对现有 fixture 输入，spec 归一化结果与 adapter 现状输出一致（迁移期）；
4. 参数映射完整性：`adjust`/日期格式等均有定义。

## 5. 迁移计划（TASK-2.18）

1. **阶段 A（契约 + spec 框架）**：冻结 API/schema（本文档）；实现 spec 加载器/校验器；为现有 5 个源 × 各 endpoint 写 spec；CI 覆盖度与金样对照；
2. **阶段 B（切换 adapter）**：adapter 内部映射改为调用 `normalize()`；删除重复的字段映射代码；金样与全量测试保持通过；
3. **阶段 C（扩展）**：新增源（BaoStock 等）只写 spec + 薄 adapter；venues 扩展（HK/US/GI/TI/WI）同步补 spec 与测试。

## 6. 设计决策（2026-09-13）

1. ✅ canonical venue 采用 Wind 标准 `.SH/.SZ/.BJ/.OF/.CSI/.HK/.O/.N/.A/.GI/.TI/.WI`，不保留 `.US`。
2. ✅ `daily_return` 统一为百分比数值（1.23 = +1.23%）。
3. ✅ spec 格式：每源一个 TOML（stdlib `tomllib`，无新依赖；支持注释；见 §4.2 示例）。
4. ✅ 本文档 API/schema 标记为 **v0 稳定契约**（后续只增不改）。

## 7. 与 v1 的边界：Pydantic 归属 FinDataPlatform / REST

- **v0 `FinDataHub` 不引入 Pydantic**：契约由类型签名 + 本文档 + `schemas.py` 显式校验 + 金样测试保证；spec 用 stdlib `tomllib` 解析 + 显式结构校验。保持核心依赖仅 `pandas`。
- **v1 `FinDataPlatform` SDK 与 REST 使用 Pydantic v2**：
  - SDK 接口模型（请求/响应）、配置模型、结果元数据模型统一用 Pydantic；
  - REST（FastAPI）直接复用同一批模型生成 OpenAPI，保证 SDK 与 REST 语义一致；
  - JSON Schema 可作为接口文档与数据字典的输入。
- **原因**：v0 是进程内库，契约靠类型与测试即可；v1 有跨语言 REST 边界，需要机器可校验的模型与 OpenAPI。

## 8. 全局枚举与常量（设计）

原则：**对外契约中的取值一律有枚举**；API 参数接受 `枚举 | 字符串值`（内部统一 coerce），spec/TOML 使用字符串值并在加载时校验。

### 8.1 枚举（`enums.py`，包根导出）

| 枚举 | 值 | 状态 | 说明 |
|---|---|---|---|
| `Source` | tushare / wind / ifind / akshare / fuyao | 已有 | 数据源 |
| `SecType` | stock / etf / lof / fund / index | 已有 | 证券类型 |
| `Venue` | SH / SZ / BJ / OF / CSI / HK / O / N / A / GI / TI / WI | **新增** | canonical 市场后缀（Wind 标准） |
| `Currency` | CNY / HKD / USD / EUR / JPY … | **新增** | ISO 4217（按需扩展） |
| `Adjust` | qfq / hfq | **新增** | 复权方式；`None` 表示不复权（不使用 `none` 成员，避免与字符串混淆） |
| `Freq` | 1d / 1w / 1mo / 1q / 1y / 1m / 5m / 15m / 30m / 60m | **新增** | v0 仅支持 `1d`；其余预留（高频接口预留） |
| `ReferenceKind` | stock_list / fund_list / index_list | **新增** | `get_reference` 的 kind |
| `Capability` | bars / snapshot / fund_nav / reference / trade_calendar / adjust_factors | **新增** | 取代 `BaseAdapter.CAP_*` 字符串常量（无历史用户，直接切换） |

### 8.2 常量（`constants.py`）

- **attrs 键**：`ATTR_SOURCE / ATTR_REQUESTED_SOURCE / ATTR_FACTOR_SOURCE / ATTR_FILLED_FROM / ATTR_CACHED / ATTR_FETCHED_AT / ATTR_CODE_FORMAT / ATTR_ADJUST`（避免各处拼字符串）。
- **venue → currency 映射**：`VENUE_CURRENCY: Mapping[Venue, Currency]`（`.GI` 不在映射内，需参考数据判定为 `None`）。
- **列名**：沿用 `schemas.py` 的 `*_COLUMNS` 元组（schema 内聚）。

### 8.3 使用约定

1. 公共 API 参数类型写 `Venue | str`、`Adjust | str | None`、`Freq | str`、`ReferenceKind | str`；字符串值实时 coerce，非法值抛 `ValueError`（消息含合法取值）。
2. 所有 attr 写入/读取使用 `constants.py` 常量，测试亦然。
3. spec（TOML）中的枚举字段在加载时用枚举校验；拼写错误立即报错。
4. v1 `FinDataPlatform`（Pydantic/数据字典）复用同一批枚举，避免两套取值定义。

## 9. 契约冻结状态（2026-09-13）

- 方法签名：**已冻结**（含 `get_adjust_factors` / `get_adjustment_events` 与两个预留接口；预留接口调用抛 `UnsupportedCapability`）。
- canonical schema / attrs / 枚举：**已定**（本文件 v0 契约，后续只增不改）。

## 10. 实施状态（2026-09-13）

- **阶段 A 已完成**：
  - 枚举：`Venue / Currency / Adjust / Freq / ReferenceKind / Capability`（`enums.py`，包根导出）；
  - 常量：`constants.py`（attrs 键、`VENUE_CURRENCY`、`currency_for_code/venue`）；
  - `codes.py` Venue 化：新 venue 推断（`.O/.N/.A`→stock、`.GI/.TI/.WI/.CSI`→index、`.HK` 需显式 sec_type）；
  - `schemas.py`：bars/snapshot/nav/reference 增加 `currency` 列（按 venue 集中推导）；
  - **spec 框架**：`fin_data_hub/specs/`（4 源 TOML：tushare/akshare/wind/fuyao）+ loader/validator/`normalize()` + 覆盖度测试；
  - facade：`get_adjust_factors` / `get_adjustment_events` 落地；`get_intraday_bars` / `get_edb_series` 预留（抛 `UnsupportedCapability`）。
- **阶段 B（已完成 2026-09-13）**：
  - spec 框架增强：`code` 字段可用 `mapper.from_source` 还原 canonical / 单标 `code=` 覆盖（响应无代码列时自动补 `code` 列）、`optional=true` 缺失置空、`bool` 兼容 `"1"/"0"` 与真值字符串；
  - 已切换 `normalize()`：Tushare（bars / fund_nav / trade_calendar / adjust_factors）、AkShare（bars / fund_nav）、Fuyao（bars / snapshot / adjustment_events；快照日期仍在 adapter 注入）；
  - **例外（保留 bespoke 映射）**：iFinD（markdown 文本 parser）；Wind（单位因子随响应 `unit` 元数据动态变化，保留 `_map_kline` / `_map_snapshot`）；AkShare/Fuyao/BaoStock 的交易日历为**派生结果**（开市日集合 → 区间逐日）非行映射。
- **TASK-2.26 扩展（2026-09-13）**：新增 `get_security_info` 与 reference kinds `etf_list` / `delist_list`（契约只增不改）。
- **TASK-2.27 扩展（2026-09-13）**：新增 reference kinds `industry_classify`（SW2021 L1/L2/L3 全量，511 条）与 `industry_member`（成分含历史：Y 5902 + N 2006，offset 分页）；`parent_code` 组装口径为上级 `industry_code`。
- **阶段 C（已完成 2026-09-13）**：
  - BaoStock spec（bars / trade_calendar / adjust_factors）+ adapter 切换（因子基准行逻辑不变）；
  - HK/US/GI/TI/WI：CodeMap（`PassthroughMapper`）覆盖与不支持源的明确报错已有测试（`test_mapping.py`）；对应 adapter 端点实现前不预置 spec；
  - CI：spec 目标列 ⊆ canonical schema（`test_specs.py`）、各源金样、全量测试通过。
