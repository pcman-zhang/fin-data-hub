---
id: doc-1
title: 多源金融数据聚合库 v0 架构设计
type: specification
created_date: '2026-09-12 10:51'
updated_date: '2026-09-12 11:43'
---
# 架构设计：多源金融数据聚合库 v0

状态：草案（待评审）。本文档为设计基线，评审通过后再拆分为实现任务。

## 1. 目标与约束

- Python 库（可 import 的模块），不含 CLI、常驻进程、调度器。
- 聚合 Tushare / Wind / 同花顺 iFinD / AkShare 四类数据源，schema 可扩展。
- 对外统一接口；`source` 参数显式标明数据来源；内部完成调度。
- 统一标的代码模型；各源代码差异由映射层收敛。
- 配置对象注入（token 等凭证不落仓库）；每源限流；多线程安全；内存缓存且支持 `force` 刷新。
- 范围：采集/聚合 API + 限流 + 内部内存缓存。**本库不包含持久化存储层**（不落库、不写文件）；需要持久化的下游程序自行落地。

## 2. 统一代码模型（WindCode）

### 2.1 规范

- 格式：`<symbol>.<VENUE>`，symbol 为 6 位补零，VENUE 大写。
- 初始 venue：`SH`、`SZ`、`BJ`、`OF`（场外基金）；预留 `CSI`、`TI`（同花顺指数）、`WI`（Wind 指数）、`HK`、`US`。
- 示例：`600000.SH`、`000001.SZ`、`920002.BJ`、`510300.SH`、`159915.SZ`、`000001.OF`、`000300.SH`、`399006.SZ`。
- 歧义必须靠后缀消解：`000001.SZ`（平安银行）≠ `000001.OF`（华夏成长）。不支持省略 venue 的裸代码。
- `SecCode` 值对象负责 parse / format / validate；`sec_type ∈ {stock, etf, lof, fund, index}` 由 venue + 代码段推断，允许显式覆盖。

### 2.2 各源兼容性（已实测）

| 数据源 | 直接接受 WindCode | 实测依据 |
|---|---|---|
| Tushare | 是 | `stock_basic`(600000.SH / 920002.BJ)、`fund_basic`(510300.SH / 000001.OF)、`index_basic`(000300.SH) 均正常返回 |
| iFinD | 是 | MCP 工具入参接受 WindCode（实测 `index_data` 000300.SH、基金净值 000001.OF）；MCP HTTP 直连已通过 `initialize`/`tools/list` 验证 |
| Wind | 是（原生 WindCode） | MCP 工具入参接受 WindCode；`https://mcp.wind.com.cn/vserver_*/mcp/` HTTP 直连已通过 `initialize` 验证（stateless SSE，`Bearer <api_key>`） |
| AkShare | 否 | 各接口参数不统一：`stock_zh_a_hist(symbol='000001')`、`fund_etf_hist_em(symbol='159707')`、`fund_open_fund_info_em(symbol='710001')`、`stock_zh_index_daily_em(symbol='csi931151')` |

结论：canonical 采用 WindCode；映射层主要服务 AkShare；Tushare / iFinD / Wind 近似直通（iFinD、Wind 经远端 MCP 接入，见 3.3），但指数与别名个例仍需规则表。

### 2.3 映射层设计

- `CodeResolver`：推断 `sec_type`；可用缓存的证券列表（stock/fund/index basic）兜底确认。
- 每个 adapter 实现 `to_source_code(SecCode, endpoint) -> str` 与 `from_source_code(raw, endpoint) -> SecCode`。
- 规则以表驱动（venue × sec_type × endpoint），集中维护，禁止散落 if-else。
- AkShare 需按 endpoint 选函数与参数名（`symbol`/`fund`/`code` 各异），映射规则单独成表。
- 无法识别的 venue/type 抛 `UnknownSecurityError`，不猜测。

## 3. 对外统一接口与内部调度

### 3.1 门面 API（草案）

```python
class DataHub:
    def get_bars(self, codes, start, end, freq="1d", adjust=None,
                 source=Source.TUSHARE, fields=None, force=False, ttl=None) -> pd.DataFrame
    def get_snapshot(self, codes, fields=None, source=..., force=False) -> pd.DataFrame
    def get_fund_nav(self, codes, start=None, end=None, source=..., force=False) -> pd.DataFrame
    def get_reference(self, kind, source=..., force=False) -> pd.DataFrame   # stock_list / fund_list / index_list
    def get_trade_calendar(self, start, end, source=..., force=False) -> pd.DataFrame
```

- `source` 显式为必填参数（`Source` 枚举：`TUSHARE` / `WIND` / `IFIND` / `AKSHARE`），避免来源混淆；预留 `HubConfig.default_source` 作为简写。
- 统一返回 `pandas.DataFrame`，规范列由 `schemas.py` 定义；`df.attrs` 携带 `source / cached / fetched_at / adjust` 等元信息。
- 规范列采用统一数据模型：序列类输出长表 `symbol / obs_date / value / unit / source`；K 线/快照以统一列名映射（OHLCV 等），不做跨源裸字段拼接。
- 调用链：`normalize codes → capability check → cache lookup → rate limit → adapter fetch → schema normalize → cache store → return`。
- 不做自动 fallback（v0）；`Source.AUTO` 作为后续扩展点。

### 3.2 内部调度

- `SourceRegistry`：`source → adapter` 实例注册表。
- adapter 实现 `BaseAdapter`（Protocol/ABC）；能力缺失抛 `UnsupportedCapability`，错误信息中列出可用 source。

### 3.3 MCP 接入层（iFinD / Wind 的运行通道）

背景：项目不引入 WindPy / iFinDPy（金融终端授权成本高），iFinD/Wind 通过厂商托管的 MCP 服务取数。已验证两者均可由普通 HTTP 客户端直接调用，不依赖任何 agent/IDE 运行时，也无需官方 `mcp` SDK。

- 协议：Streamable HTTP + JSON-RPC 2.0；`initialize` → `notifications/initialized` → `tools/call`；兼容 `application/json` 与 `text/event-stream`（SSE 取 `data:` 行）。
- iFinD：`POST https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-{stock,fund,edb,news,bond,global-stock,index,futures}-mcp`；**`Authorization: <token>` 裸 token（不加 Bearer）**；`initialize` 返回 `Mcp-Session-Id`，按服务缓存会话复用（参考 30 分钟 TTL）。
- Wind：`POST https://mcp.wind.com.cn/vserver_{stock_data,fund_data,index_data,bond_data,financial_docs,economic_data,analytics_data}/mcp/`；`Authorization: Bearer <api_key>`；服务端 stateless（SSE 响应），无需会话。
- 凭证来源：调用方显式注入（首选）或环境变量（统一前缀 `FIN_DATA_HUB_`，如 `FIN_DATA_HUB_WIND_API_KEY`、`FIN_DATA_HUB_IFIND_TOKEN`）；开发期可提供便利 loader，但库核心不隐式扫描用户目录。
- 库内实现 `mcp/client.py`：统一 JSON-RPC 客户端，负责会话（按 server 缓存 + TTL）、JSON/SSE 双解析、超时、重试（参考 2 次 + 线性退避）、`content[0].text` 解包、错误映射（HTTP / JSON-RPC `error` / 业务信封）。
- 输出解析（实测结构，parser 必须按源区分）：
  - Wind：`content[0].text` 多为 JSON 字符串；EDB 新版结构 `{data: {date: [...], indicatorInfo: [{code, name, data: [...]}]}}`。
  - iFinD：外层 `{code:1,msg:"success",data:...}`；stock/index/fund 的 `data` 为 JSON 字符串（内含 `answer` markdown 表，需 parser）；edb 的 `data` 为对象（`datas[].data.{columns,data}`）。
- 限流：Wind 契约给出并发上限 10 与 `RATE_LIMIT_ERROR`；iFinD 为月度按次配额（非 QPS），两者都走 §5 限流器与 §3.4 配额计数。
- 依赖：MCP 客户端用 `httpx`（线程安全、支持流式），按源提供 extras `ifind` / `wind`（各自包含 httpx）；不引入官方 `mcp` SDK（async-first，不适配同步 pandas 库）。
- v0 范围：先映射行情/K 线/快照/基础资料等高频端点，落到 3.1 的 `get_bars` / `get_snapshot` / `get_reference` / `get_fund_nav`。

### 3.4 请求合并、配额与成本

前期经验的核心结论：**调用次数就是成本**。适配器必须按各源/端点能力边界合并请求，并在库内计量。

- 能力边界（capability 元数据，驱动分块/合并）：
  - Wind：行情/K 线类 `windcode` 支持逗号批量（单次 ≤50）；EDB `get_economic_data` 支持精确代码逗号批量，**优先于旧 `query` 类接口（单位成本显著更高）**；`get_bond_market_data` 单次约 100 行截断，长区间按 ≤90 天分块（用中文日期）。
  - iFinD：全部为 NL 调用，**多主体/多指标/多期尽量合并为一次 query**；EDB 一次只能一个指标（时间范围可合并）；指数/ETF/股票多标的聚合有效。
- 配额与计量：每源调用计数器（按次/按积分），记录 `{source, endpoint, codes, latency, est_cost}`；预算阈值可配置并告警；`hub.stats()` 暴露。
- 计价提示：各接口单位成本不同（`query` 类显著高于 `get` 类；按次计费源 1 次 = 1 额度）。适配器声明 `cost_hint`，为后续路由/降级预留。
- 缓存即省钱：付费源默认 TTL 6h，`force` 慎用。
- v0 只要求显式 `source`；上述合并与计量在单源内部生效。指标级"主源→备源→兜底"路由见 §10 待确认项。

## 4. 配置与凭证

```python
@dataclass
class HubConfig:
    tushare: TushareConfig | None
    wind: WindConfig | None
    ifind: IFindConfig | None
    akshare: AkShareConfig
    default_source: Source | None
    cache: CacheConfig
```

- 设计决策：token 由调用方通过构造参数/配置对象传入；库不读取任何外部全局配置，也不隐式扫描用户目录。
- 优先级：显式传参 > 环境变量（如 `FIN_DATA_HUB_TUSHARE_TOKEN`）> 本地配置文件（如 `config.local.toml`，列入 `.gitignore`）。
- AkShare 无 token；其余源缺凭证且被调用时抛 `MissingCredentialError`。
- 凭证安全：不写日志、`repr` 脱敏（`token='***'`）；仓库与代码中禁止出现真实 token。
- 在 v0 即留好全部源的配置透传参数（timeout、max_retries、rate_limit 等），即使适配器后续才实现。

## 5. 限流（QPS / RateLimit）

- `RateLimiter`：线程安全令牌桶（或滑动窗口），每源一个实例。
- 支持 endpoint 级覆盖：Tushare 限额按接口与积分档不同（如 `{"default": 5, "endpoints": {"stock_basic": 0.5}}`）。
- 限流与配额是两件事：QPS 限流防封禁；配额/成本计数防额度超支（按次/按积分计费的源，见 §3.4）。
- 配置项：`qps`、`burst`、`max_wait`；阻塞获取，超时抛 `RateLimitTimeout`。
- AkShare 默认保守（建议 1 QPS + 低并发），因其抓取公开站点且无官方配额；Tushare/Wind/iFinD 默认值保守起步，按账号实际配额调整。
- 服务端限流（429 / 业务错误码）→ 指数退避 + jitter + `max_retries`；返回 `Retry-After` 时遵循。
- 限流为进程内：多进程/多实例会叠加配额，文档中注明。

## 6. 多线程安全

- cache、limiter、registry 等共享状态全部加锁。
- 缓存提供 single-flight：同一 key 并发未命中时仅一个线程真实请求，其余等待结果，防止并发击穿烧配额。
- 批量查询用 `ThreadPoolExecutor`；每源 `max_concurrency` 上限独立于 QPS 配置。
- Tushare SDK 已核实为无状态（每次调用直接 `requests.post`，无共享 Session），可安全并发，无需额外锁。
- AkShare 走其 Python 包（HTTP 抓取）；iFinD / Wind 走库内 MCP 客户端：`httpx.Client` 可共享，但 iFinD 的 `Mcp-Session-Id` 与客户端实例绑定，按连接隔离，禁止跨线程复用不一致的会话状态。
- DataFrame 不跨线程共享修改；缓存存取做防御性拷贝。

## 7. 内存缓存

- `MemoryCache`：TTL + LRU 容量上限，线程安全；**仅进程内内存，不落盘、不跨进程共享**。
- 实现选型：**标准库自研，不引入缓存库**。理由：per-entry TTL（按端点/数据类型分级）、per-call `ttl` 覆盖、single-flight、`force` 语义均需自行封装，通用库仅省少量 LRU 代码却增加依赖；核心依赖保持仅 `pandas`。实现要素：`OrderedDict` + `time.monotonic()` + `threading.Lock`（LRU），single-flight 用 `dict[key, Future]` + 锁（首请求者执行，其余等待，异常 `set_exception` 后清理）。
- **内存限制采用"字节预算为主、条数兜底"双约束**（仅条数无法约束内存，DataFrame 大小差异巨大）：
  - 写入前计算 `size_fn(value)`，默认 `df.memory_usage(deep=True, index=True).sum()` 乘安全系数（object 列低估）；维护 `_sizes[key]` 与 `_total_bytes`；非 DataFrame 值用 `sys.getsizeof`。
  - 淘汰：写入时 `while _total_bytes + new > max_bytes or len > max_entries: popitem(last=False)`，同步扣减；覆盖写先扣旧值。
  - `max_entry_bytes`：单条超限则跳过缓存（仍正常返回），防止单个大请求挤空缓存。
  - TTL 与释放：容量是硬边界（未访问的过期条目也不会超预算）；`get` 惰性删除过期项，另每 N 次写入做一次过期清扫（条目数有界，O(n) 开销可忽略）。
- 副本策略：以 `pandas>=3.0` CoW 为前置（已实测：`df.values` 只读；赋值 / 浅拷贝 / `to_numpy` 修改均不污染缓存）→ 默认**直接返回缓存对象、不做深拷贝**，缓存仅占一份；配置 `copy_on_return=True` 可强制隔离（内存峰值约 2x）。
- Key：`(source, endpoint, canonical_params)`；参数规范化（codes 排序、日期归一，`adjust/freq/fields` 入 key）。
- TTL 分级：付费源默认 6h（缓存 = 省额度/成本）；参考数据（证券列表/交易日历）约 12h；日线收盘后 TTL 至下一交易日；实时快照 30–60s；净值按披露节奏。支持 per-call `ttl` 覆盖。
- `force=True`：跳过读取并强制刷新覆盖；`df.attrs["cached"]` 标识命中。
- 可选负缓存（短 TTL），避免持续重试失败源。
- 返回值与缓存值相互隔离（深拷贝或只读），防止调用方修改污染缓存。

## 8. 代码结构（建议）

```
pyproject.toml            # src 布局；pandas 必装，各源依赖作为可选 extras
src/fin_data_hub/
  __init__.py             # 导出 DataHub / HubConfig / Source / SecCode
  facade.py               # DataHub 门面与调用链
  config.py               # HubConfig 及子配置、环境变量加载
  codes.py                # SecCode / venue / 类型推断
  mapping.py              # 各源代码映射规则
  cache.py                # MemoryCache + single-flight
  ratelimit.py            # RateLimiter + 退避重试
  schemas.py              # 各 endpoint 规范列与类型
  errors.py
  mcp/
    client.py             # MCP over HTTP JSON-RPC 客户端（iFinD / Wind 共用）
    parsers/              # iFinD markdown → DataFrame 解析器
  sources/
    base.py               # BaseAdapter
    registry.py
    tushare.py
    akshare.py
    ifind.py              # iFinD MCP adapter
    wind.py               # Wind MCP adapter
```

- 无 CLI、无调度器；对外只暴露可 import 的 API。

### 8.1 依赖声明与开发环境（设计决策）

- 库项目必须在 `pyproject.toml` 声明依赖：
  - `[project].dependencies`：运行时必需，仅 `pandas`（若直接 `import numpy` 则显式加入）。
  - `[project.optional-dependencies]`：按源拆分 `tushare`、`akshare`、`ifind`（httpx）、`wind`（httpx）；`dev` = pytest + ruff（mypy 可选）。
  - WindPy / iFinDPy **不在 PyPI 且本机不采用**：iFinD/Wind 走远端 MCP（见 3.3），无 SDK 依赖。
- 不提交 lock 文件（库的惯例，lock 属于应用侧）；版本采用区间约束（如 `pandas>=3.0,<4`，CoW 为缓存零拷贝的前提），`requires-python = ">=3.11"`。
- 开发环境需要隔离，但**不需要 conda**（无系统级二进制依赖）：用标准库 `python3 -m venv .venv`，再 `pip install -e ".[dev,tushare,akshare,ifind,wind]"`。
- 消费方按需安装：`pip install fin-data-hub[wind]` / `[ifind]` 等即可，无需安装任何 agent/IDE 运行时、Node CLI 或厂商 SDK；前提是持有对应数据服务的凭证与访问权限（商业前提，非安装步骤）。
- `.gitignore`：`.venv/`、`__pycache__/`、`*.egg-info/`、`dist/`、`build/`。
- 消费方在自己的环境中安装本库；本仓库的开发环境选择不影响调用方。

## 9. 测试与验证

- 离线单元测试：代码映射、限流器（注入时钟）、缓存 TTL/force/single-flight、schema 规范化（mock adapter）。
- 适配器解析测试使用固定响应 fixture（录制 JSON），不依赖外网。
- 集成测试标记 `integration`，需要凭证时默认跳过（`pytest -m "not integration"`）。
- 脚手架：`pyproject.toml`（hatchling 或 setuptools）、pytest、ruff；mypy 可选。
- 预计命令：`python3 -m pip install -e ".[dev]"`；`pytest`；单测 `pytest tests/test_codes.py -q`。

## 10. 开放问题（需确认）

1. 时间列统一为 `datetime64[ns]` 还是 `YYYYMMDD` 字符串？（倾向 datetime64）
2. 指数跨源映射（iFinD `.TI` / Wind `.WI` / 中证 `.CSI`）是否纳入 v0？
3. 复权口径统一为 `adjust ∈ {None, qfq, hfq}`，Tushare 侧用 `adj_factor` 换算是否接受？
4. ~~存储层是否纳入本轮~~ 已确认：**本库不含存储层**，缓存仅在进程内内存维护。
5. 是否需要 `source="auto"` 回退链？（v0 建议不做，仅留扩展点）
6. 是否需要多进程配额协调？（v0 建议不做，文档注明限制）
7. iFinD MCP 返回 markdown 文本表，v0 的解析覆盖范围（优先行情/K 线/快照）与容错策略是否接受？
8. ~~是否通过 MCP 接入 iFinD/Wind~~ 已确认：本机无 SDK，iFinD/Wind 以远端 MCP 为一等接入通道（见 3.3）。
9. 是否将"配额/成本计量 + 预算告警"纳入 v0？（成本治理是重要卖点；建议纳入，见 3.4）
10. 指标级路由/降级链（主源→备源→兜底）与显式 `source` 的关系：v0 保持显式 source，Phase 2 以配置增加策略路由（`source="auto"` + 优先级）？
11. 是否对外同时提供 Python SDK 与 streamable HTTP MCP server？若提供，MCP server 作为独立包装项目还是本库可选模块？
12. 是否有既有适配器实现需要迁移进本项目（复用/重写）？迁移范围与顺序？

## 11. 建议任务拆分（评审通过后创建）

1. 脚手架：pyproject + src 布局 + errors/枚举
2. codes + mapping（含单测）
3. cache + ratelimit + single-flight（含单测）
4. DataHub 门面 + 调度 + schema 规范化（含单测）
5. MCP 传输层：`mcp/client.py`（initialize/session/SSE/错误映射）+ iFinD markdown parser（fixture 测试）
6. Tushare 适配器
7. AkShare 适配器（fixture 测试）
8. iFinD MCP 适配器（基于 MCP 传输层；含 markdown parser）
9. Wind MCP 适配器（基于 MCP 传输层；get 优先）
10. 成本/配额计量与预算告警
11. 请求合并与 capability 元数据（批量/分块/合并，含单测）
12. 集成测试与使用文档
13. 对账框架（跨源差异统计，切换/迁移前必做）
