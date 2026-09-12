"""MCP over HTTP 客户端（iFinD / Wind 共用）。

协议：Streamable HTTP + JSON-RPC 2.0
    ``initialize`` → ``notifications/initialized`` → ``tools/call``

- 兼容 ``application/json`` 与 ``text/event-stream``（SSE）两种响应；
- 会话（``Mcp-Session-Id``）按客户端缓存并设 TTL，过期自动重建；无会话的
  stateless 服务（如 Wind）自动跳过；
- 鉴权支持 ``Bearer``（Wind）与裸 token（iFinD）；
- 不依赖官方 ``mcp`` SDK，仅使用 ``httpx``。
"""

from __future__ import annotations

import contextlib
import itertools
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from fin_data_hub.errors import NetworkError, ResponseParseError, SourceError
from fin_data_hub.ratelimit import retry_call

AuthScheme = Literal["bearer", "raw"]


@dataclass(frozen=True, slots=True)
class McpServerConfig:
    """单个 MCP 服务端点的配置。"""

    name: str
    url: str
    token: str = field(repr=False)
    auth_scheme: AuthScheme = "bearer"
    protocol_version: str = "2024-11-05"
    timeout: float = 30.0
    max_attempts: int = 2
    session_ttl: float = 30 * 60
    client_name: str = "fin-data-hub"


@dataclass(frozen=True, slots=True)
class McpSession:
    session_id: str
    created_at: float


class McpHttpClient:
    """线程安全的 MCP HTTP JSON-RPC 客户端。"""

    def __init__(
        self,
        config: McpServerConfig,
        *,
        http_client: httpx.Client | None = None,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self._client = http_client or httpx.Client(timeout=config.timeout)
        self._owns_client = http_client is None
        self._time_fn = time_fn
        self._sleep_fn = sleep_fn
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self._session: McpSession | None = None

    # --------------------------------------------------------------- 对外 API
    def call_tool(self, tool: str, arguments: dict[str, Any] | None = None) -> dict:
        """调用 MCP 工具，返回 JSON-RPC ``result``（未解包 content）。"""
        if not tool:
            raise ValueError("tool 不能为空")
        session_id = self._ensure_session()
        body, _ = self._call(
            {
                "jsonrpc": "2.0",
                "id": next(self._ids),
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments or {}},
            },
            session_id=session_id,
        )
        result = body.get("result")
        if not isinstance(result, dict):
            raise ResponseParseError(f"MCP 响应缺少 result: {str(body)[:200]}")
        if result.get("isError"):
            raise SourceError(
                f"MCP 工具 {tool!r} 返回错误: {_extract_text(result)[:200]}"
            )
        return result

    def list_tools(self) -> list[dict]:
        """列出服务端工具（开发期探测用）。"""
        session_id = self._ensure_session()
        body, _ = self._call(
            {"jsonrpc": "2.0", "id": next(self._ids), "method": "tools/list"},
            session_id=session_id,
        )
        tools = (body.get("result") or {}).get("tools")
        if not isinstance(tools, list):
            raise ResponseParseError(f"tools/list 响应异常: {str(body)[:200]}")
        return tools

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> McpHttpClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ---------------------------------------------------------------- 会话
    def _ensure_session(self) -> str | None:
        with self._lock:
            session = self._session
            if session is not None and (
                self._time_fn() - session.created_at < self.config.session_ttl
            ):
                return session.session_id
            self._session = None

        body, session_id = self._call(
            {
                "jsonrpc": "2.0",
                "id": next(self._ids),
                "method": "initialize",
                "params": {
                    "protocolVersion": self.config.protocol_version,
                    "capabilities": {},
                    "clientInfo": {
                        "name": self.config.client_name,
                        "version": _package_version(),
                    },
                },
            },
            session_id=None,
        )
        if "result" not in body:
            raise ResponseParseError(f"initialize 响应异常: {str(body)[:200]}")

        if session_id:
            with contextlib.suppress(SourceError):
                self._post(
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    session_id=session_id,
                )
            with self._lock:
                self._session = McpSession(
                    session_id=session_id, created_at=self._time_fn()
                )
        return session_id

    # ---------------------------------------------------------------- 传输
    def _call(
        self, payload: dict, *, session_id: str | None
    ) -> tuple[dict, str | None]:
        """发送 JSON-RPC 请求并归一化错误；网络失败按配置重试。"""

        def do_call() -> tuple[dict, str | None]:
            resp = self._post(payload, session_id=session_id)
            if resp.status_code >= 400:
                raise SourceError(f"MCP HTTP {resp.status_code}: {resp.text[:200]}")
            body = self._parse_body(resp)
            error = body.get("error")
            if isinstance(error, dict):
                raise SourceError(
                    f"MCP JSON-RPC 错误 {error.get('code')}: {error.get('message')}"
                )
            return body, resp.headers.get("mcp-session-id")

        return retry_call(
            do_call,
            attempts=self.config.max_attempts,
            retry_on=(NetworkError,),
            sleep_fn=self._sleep_fn,
        )

    def _post(self, payload: dict, *, session_id: str | None) -> httpx.Response:
        try:
            return self._client.post(
                self.config.url,
                json=payload,
                headers=self._headers(session_id=session_id),
            )
        except httpx.HTTPError as exc:
            raise NetworkError(f"MCP 请求失败: {exc}") from exc

    def _headers(self, *, session_id: str | None) -> dict[str, str]:
        token = self.config.token
        authorization = (
            f"Bearer {token}" if self.config.auth_scheme == "bearer" else token
        )
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return headers

    def _parse_body(self, resp: httpx.Response) -> dict:
        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            for line in resp.text.splitlines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(data, dict) and ("result" in data or "error" in data):
                    return data
            raise ResponseParseError(
                f"无法从 SSE 响应解析 JSON-RPC 消息: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise ResponseParseError(f"MCP 响应不是 JSON: {resp.text[:200]}") from exc
        if not isinstance(data, dict):
            raise ResponseParseError(f"MCP 响应结构异常: {str(data)[:200]}")
        return data


def _extract_text(result: dict) -> str:
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            return str(first.get("text", ""))
    return str(result)


def unwrap_content(result: dict) -> Any:
    """解包 MCP ``content`` 文本：JSON 字符串 → Python 对象，否则原样返回文本。

    若响应带 ``structuredContent``，优先返回该结构。
    """
    if not isinstance(result, dict):
        return result
    if "structuredContent" in result:
        return result["structuredContent"]
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text", "")
            try:
                return json.loads(text)
            except (ValueError, TypeError):
                return text
    return result


def _package_version() -> str:
    try:
        from fin_data_hub._version import __version__

        return __version__
    except Exception:  # pragma: no cover - 理论不可达
        return "0"
