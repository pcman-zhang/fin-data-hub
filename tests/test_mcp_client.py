import json

import httpx
import pytest

from fin_data_hub.errors import NetworkError, ResponseParseError, SourceError
from fin_data_hub.mcp import McpHttpClient, McpServerConfig, unwrap_content


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class ServerStub:
    """httpx.MockTransport 处理器，模拟 MCP Streamable HTTP 服务。"""

    def __init__(self, *, sse: bool = False, stateless: bool = False) -> None:
        self.sse = sse
        self.stateless = stateless
        self.requests: list[tuple[dict, dict]] = []
        self.initialize_count = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append((body, dict(request.headers)))
        method = body.get("method")
        if method == "initialize":
            self.initialize_count += 1
            headers = {}
            if not self.stateless:
                headers["mcp-session-id"] = f"sess-{self.initialize_count}"
            return self._respond(
                {
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "serverInfo": {"name": "stub", "version": "1"},
                    },
                },
                headers,
            )
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "tools/list":
            return self._respond(
                {
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"tools": [{"name": "echo"}]},
                }
            )
        if method == "tools/call":
            name = body["params"]["name"]
            if name == "echo":
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"echo": body["params"]["arguments"]}),
                        }
                    ]
                }
            elif name == "plain":
                result = {"content": [{"type": "text", "text": "hello"}]}
            elif name == "error":
                result = {
                    "isError": True,
                    "content": [{"type": "text", "text": "boom"}],
                }
            else:
                return self._respond(
                    {
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "error": {"code": -32601, "message": "no such tool"},
                    }
                )
            return self._respond(
                {"jsonrpc": "2.0", "id": body["id"], "result": result}
            )
        raise AssertionError(f"unexpected method: {method}")

    def _respond(
        self, payload: dict, headers: dict | None = None
    ) -> httpx.Response:
        extra = dict(headers or {})
        if self.sse:
            text = "event: message\ndata: " + json.dumps(payload) + "\n\n"
            extra["content-type"] = "text/event-stream"
            return httpx.Response(200, text=text, headers=extra)
        return httpx.Response(200, json=payload, headers=extra)


def make_client(
    handler,
    *,
    auth_scheme: str = "raw",
    clock: FakeClock | None = None,
    **config_kwargs,
) -> tuple[McpHttpClient, httpx.Client]:
    config = McpServerConfig(
        name="test",
        url="https://mcp.test/srv",
        token="tok-123",
        auth_scheme=auth_scheme,
        **config_kwargs,
    )
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = McpHttpClient(
        config,
        http_client=http_client,
        time_fn=clock or (lambda: 0.0),
        sleep_fn=lambda _: None,
    )
    return client, http_client


def test_call_tool_flow_and_session_header() -> None:
    stub = ServerStub()
    client, http_client = make_client(stub)
    with client:
        result = client.call_tool("echo", {"a": 1})

    assert stub.initialize_count == 1
    call_body, call_headers = stub.requests[-1]
    assert call_body["method"] == "tools/call"
    assert call_headers["mcp-session-id"] == "sess-1"
    assert unwrap_content(result) == {"echo": {"a": 1}}
    http_client.close()


def test_sse_response_parsed() -> None:
    stub = ServerStub(sse=True)
    client, http_client = make_client(stub)
    with client:
        result = client.call_tool("plain")
    assert unwrap_content(result) == "hello"
    http_client.close()


def test_auth_scheme_raw_and_bearer() -> None:
    stub_raw = ServerStub()
    client_raw, http_raw = make_client(stub_raw, auth_scheme="raw")
    with client_raw:
        client_raw.call_tool("plain")
    assert stub_raw.requests[0][1]["authorization"] == "tok-123"
    http_raw.close()

    stub_bearer = ServerStub()
    client_bearer, http_bearer = make_client(stub_bearer, auth_scheme="bearer")
    with client_bearer:
        client_bearer.call_tool("plain")
    assert stub_bearer.requests[0][1]["authorization"] == "Bearer tok-123"
    http_bearer.close()


def test_session_reused_and_rebuilt_after_ttl() -> None:
    stub = ServerStub()
    clock = FakeClock()
    client, http_client = make_client(stub, clock=clock, session_ttl=100)
    with client:
        client.call_tool("plain")
        client.call_tool("plain")
        assert stub.initialize_count == 1
        clock.advance(101)
        client.call_tool("plain")
        assert stub.initialize_count == 2
    http_client.close()


def test_stateless_server_without_session() -> None:
    stub = ServerStub(stateless=True)
    client, http_client = make_client(stub)
    with client:
        client.call_tool("plain")
    call_headers = stub.requests[-1][1]
    assert "mcp-session-id" not in call_headers
    http_client.close()


def test_http_error_maps_to_source_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server exploded")

    client, http_client = make_client(handler)
    with client, pytest.raises(SourceError, match="500"):
        client.call_tool("plain")
    http_client.close()


def test_jsonrpc_error_maps_to_source_error() -> None:
    stub = ServerStub()
    client, http_client = make_client(stub)
    with client, pytest.raises(SourceError, match="JSON-RPC"):
        client.call_tool("missing-tool")
    http_client.close()


def test_tool_is_error_flag_maps_to_source_error() -> None:
    stub = ServerStub()
    client, http_client = make_client(stub)
    with client, pytest.raises(SourceError, match="boom"):
        client.call_tool("error")
    http_client.close()


def test_network_error_retried() -> None:
    state = {"connect_errors": 0}
    stub = ServerStub()

    def handler(request: httpx.Request) -> httpx.Response:
        if state["connect_errors"] == 0:
            state["connect_errors"] += 1
            raise httpx.ConnectError("connection refused", request=request)
        return stub(request)

    client, http_client = make_client(handler, max_attempts=2)
    with client:
        result = client.call_tool("plain")
    assert unwrap_content(result) == "hello"
    assert state["connect_errors"] == 1
    http_client.close()


def test_network_error_raises_after_attempts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    client, http_client = make_client(handler, max_attempts=2)
    with client, pytest.raises(NetworkError):
        client.call_tool("plain")
    http_client.close()


def test_unparseable_body_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text="not-json", headers={"content-type": "text/html"}
        )

    client, http_client = make_client(handler)
    with client, pytest.raises(ResponseParseError):
        client.call_tool("plain")
    http_client.close()


def test_list_tools() -> None:
    stub = ServerStub()
    client, http_client = make_client(stub)
    with client:
        tools = client.list_tools()
    assert tools == [{"name": "echo"}]
    http_client.close()


def test_unwrap_structured_content_priority() -> None:
    result = {
        "structuredContent": {"value": 1},
        "content": [{"type": "text", "text": "ignored"}],
    }
    assert unwrap_content(result) == {"value": 1}


def test_config_repr_hides_token() -> None:
    config = McpServerConfig(name="x", url="https://example.com", token="secret-token")
    assert "secret-token" not in repr(config)
