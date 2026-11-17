"""Tests for the Backstage backend, with Backstage faked by monkeypatching httpx.get."""

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from idp_mcp import platform
from idp_mcp.server import mcp

ENTITIES = {
    "items": [
        {
            "kind": "Component",
            "metadata": {
                "name": "payments-api",
                "description": "Payments",
                "annotations": {"idp.demo/ai-access": "guarded"},
            },
            "spec": {"owner": "group:team-payments", "system": "shop", "lifecycle": "production"},
        },
        {
            "kind": "Component",
            "metadata": {"name": "orders-web", "annotations": {"idp.demo/ai-access": "open"}},
            "spec": {"owner": "team-storefront", "system": "shop"},
        },
        {  # no ai-access annotation: must be treated as guarded
            "kind": "Component",
            "metadata": {"name": "unlabelled-svc"},
            "spec": {"owner": "team-platform", "system": "shop"},
        },
    ]
}


@pytest.fixture
def fake_backstage(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append({"url": url, "params": params, "headers": headers})
        req = httpx.Request("GET", url)
        if url.endswith("/api/catalog/entities/by-query"):
            return httpx.Response(200, json=ENTITIES, request=req)
        if "/api/proxy/svc/orders-web" in url:
            return httpx.Response(200, text="orders-web ok", request=req)
        return httpx.Response(404, request=req)

    monkeypatch.setenv("BACKSTAGE_URL", "http://backstage:7007/")
    monkeypatch.setenv("BACKSTAGE_TOKEN", "t0ken")
    monkeypatch.setattr(platform.httpx, "get", fake_get)
    return calls


def test_list_services_from_backstage(fake_backstage):
    services = platform.list_services()
    assert [s["name"] for s in services] == ["payments-api", "orders-web", "unlabelled-svc"]
    assert services[0]["owner"] == "team-payments"  # "group:" prefix removed
    assert [s["ai_access"] for s in services] == ["guarded", "open", "guarded"]
    assert fake_backstage[0]["headers"] == {"Authorization": "Bearer t0ken"}


def test_call_service_goes_through_backstage_proxy(fake_backstage):
    result = platform.call_service("orders-web", "/")
    assert result == {
        "service": "orders-web",
        "path": "/",
        "status": 200,
        "body": "orders-web ok",
    }
    assert fake_backstage[-1]["url"] == "http://backstage:7007/api/proxy/svc/orders-web/"


@pytest.mark.parametrize("name", ["payments-api", "unlabelled-svc"])
def test_guarded_services_are_refused_and_never_called(fake_backstage, name):
    with pytest.raises(platform.PlatformError, match="guarded"):
        platform.call_service(name, "/")
    assert not any("/api/proxy/" in c["url"] for c in fake_backstage)


@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("not-in-catalog", "/"),
        ("../admin", "/"),
        ("orders-web", "/../../catalog"),
        ("orders-web", "http://evil"),
    ],
)
def test_call_service_rejects_unknown_names_and_bad_paths(fake_backstage, name, path):
    with pytest.raises(platform.PlatformError):
        platform.call_service(name, path)


@pytest.mark.asyncio
async def test_call_service_tool_reports_errors_to_the_agent(fake_backstage):
    # Over MCP this becomes an is_error result whose text the agent reads.
    with pytest.raises(ToolError, match="Unknown service 'nope'"):
        await mcp.call_tool("call_service", {"name": "nope"})


def test_backstage_down_is_a_clear_error(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setenv("BACKSTAGE_URL", "http://backstage:7007")
    monkeypatch.setattr(platform.httpx, "get", boom)
    with pytest.raises(platform.PlatformError, match="not reachable"):
        platform.list_services()
