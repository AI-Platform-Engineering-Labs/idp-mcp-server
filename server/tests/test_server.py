"""Smoke tests for the scaffold. They call the tools through the MCP server object,
the same path a real client takes, and hit the HTTP app like App Service does."""

import pytest
from starlette.testclient import TestClient

from idp_mcp.server import mcp


def _text(result) -> str:
    # call_tool returns a CallToolResult: text content blocks plus structured output.
    assert not result.is_error
    return " ".join(getattr(c, "text", "") for c in result.content)


@pytest.mark.asyncio
async def test_tools_are_registered():
    names = {t.name for t in await mcp.list_tools()}
    assert {
        "hello",
        "list_services",
        "get_service",
        "get_service_status",
        "list_teams",
        "create_service",
        "get_request_status",
    } <= names
    assert "call_service" not in names  # agents no longer call business services directly


@pytest.mark.asyncio
async def test_hello():
    assert "Hello, Ravi" in _text(await mcp.call_tool("hello", {"name": "Ravi"}))


@pytest.mark.asyncio
async def test_list_services_filters_by_owner():
    text = _text(await mcp.call_tool("list_services", {"owner": "team-payments"}))
    assert "payments-api" in text
    assert "orders-web" not in text


def test_healthz():
    app = mcp.streamable_http_app(host="0.0.0.0", stateless_http=True, json_response=True)
    with TestClient(app) as client:
        r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
