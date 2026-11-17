"""The approval flow: an agent can request a write, only a human (admin endpoint) can approve."""

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from starlette.testclient import TestClient

from idp_mcp import approvals
from idp_mcp.server import mcp

PARAMS = {"template": "python-service", "name": "new-svc", "owner": "team-payments"}


@pytest.fixture(autouse=True)
def clean():
    approvals.clear()
    yield
    approvals.clear()


@pytest.fixture
def client():
    app = mcp.streamable_http_app(host="0.0.0.0", stateless_http=True, json_response=True)
    with TestClient(app) as c:
        yield c


def _text(result) -> str:
    assert not result.is_error
    return " ".join(getattr(c, "text", "") for c in result.content)


@pytest.mark.asyncio
async def test_create_service_only_queues_a_request():
    text = _text(await mcp.call_tool("create_service", PARAMS))
    assert "pending_approval" in text
    [request] = approvals.pending()
    assert request["status"] == "pending_approval"
    assert request["result"] is None  # nothing was executed


@pytest.mark.asyncio
async def test_create_service_rejects_a_bad_template():
    with pytest.raises(ToolError, match="Unknown template"):
        await mcp.call_tool("create_service", {**PARAMS, "template": "evil"})
    assert approvals.pending() == []


@pytest.mark.asyncio
async def test_agent_tools_cannot_approve():
    names = {t.name for t in await mcp.list_tools()}
    assert not any("approve" in n for n in names)
    assert {"create_service", "get_request_status"} <= names


@pytest.mark.asyncio
async def test_get_request_status_follows_the_decision():
    request = approvals.create("create_service", PARAMS)
    assert "pending_approval" in _text(
        await mcp.call_tool("get_request_status", {"request_id": request["id"]})
    )
    approvals.decide(request["id"], True)
    assert "approved" in _text(
        await mcp.call_tool("get_request_status", {"request_id": request["id"]})
    )
    with pytest.raises(ToolError, match="Unknown request"):
        await mcp.call_tool("get_request_status", {"request_id": "req-nope"})


def test_decide_only_works_once():
    request = approvals.create("create_service", PARAMS)
    assert approvals.decide(request["id"], False)["status"] == "denied"
    assert approvals.decide(request["id"], True) is None


def test_admin_endpoints_do_not_exist_without_a_token(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert client.get("/admin/approvals").status_code == 404
    assert client.post("/admin/approvals/req-x/approve").status_code == 404


def test_admin_endpoints_need_the_right_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    request = approvals.create("create_service", PARAMS)
    url = f"/admin/approvals/{request['id']}/approve"
    assert client.post(url).status_code == 401
    assert client.post(url, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert approvals.get(request["id"])["status"] == "pending_approval"
    ok = client.post(url, headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "approved"


def test_admin_deny_and_unknown_id(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    h = {"Authorization": "Bearer s3cret"}
    request = approvals.create("create_service", PARAMS)
    assert (
        client.post(f"/admin/approvals/{request['id']}/deny", headers=h).json()["status"]
        == "denied"
    )
    assert client.post("/admin/approvals/req-none/approve", headers=h).status_code == 404
    assert client.post(f"/admin/approvals/{request['id']}/maybe", headers=h).status_code == 400
