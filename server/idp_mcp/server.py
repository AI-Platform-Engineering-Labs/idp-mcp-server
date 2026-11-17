"""The MCP server.

Platform actions for an AI agent, backed by the IDP (Backstage) through idp_mcp.platform:
  * open, read-only:  hello, list_services, get_service, get_service_status, list_teams
  * needs a human:    create_service (queues a request), get_request_status
A human approves or denies a request through the admin endpoint (scripts/approve.sh).

Two transports, same tools:
  * stdio            -> a local client (VS Code, Claude Desktop) starts this process itself
  * streamable-http  -> the server listens on http://HOST:PORT/mcp (Docker, Azure App Service)
"""

import argparse
import hmac
import os

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from idp_mcp import __version__, approvals, platform

mcp = MCPServer(
    name="idp-mcp-server",
    version=__version__,
    instructions=(
        "Tools for the Internal Developer Platform. Read tools (list_services, get_service, "
        "get_service_status, list_teams) are safe to call. create_service does NOT create "
        "anything: it queues a request that a human must approve. After calling it, tell the "
        "user the request id and that approval is needed; use get_request_status to check."
    ),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
# Asks the platform to change something: clients should confirm, and a human approves anyway.
WRITE_NEEDS_APPROVAL = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, openWorldHint=False
)


@mcp.tool(annotations=READ_ONLY)
def hello(name: str = "platform engineer") -> str:
    """Say hello. Use this to check the MCP connection works end to end."""
    return f"Hello, {name}! idp-mcp-server {__version__} is up."


@mcp.tool(annotations=READ_ONLY)
def list_services(owner: str | None = None) -> list[dict]:
    """List services in the platform's software catalog (Backstage), optionally filtered
    by owning team, e.g. owner="team-payments"."""
    services = platform.list_services()
    if owner:
        services = [s for s in services if s.get("owner") == owner]
    return services


@mcp.tool(annotations=READ_ONLY)
def get_service(name: str) -> dict:
    """Details of one service from the catalog: owner, on-call contact, tier, lifecycle, tags,
    runbook links, what it depends on and what depends on it (what breaks if it goes down).
    Use list_services to find valid names."""
    return platform.get_service(name)


@mcp.tool(annotations=READ_ONLY)
def get_service_status(name: str) -> dict:
    """Is a service healthy right now? The platform checks it for you and returns healthy
    (true/false) and the HTTP status. It does not return the service's data."""
    return platform.get_service_status(name)


@mcp.tool(annotations=READ_ONLY)
def list_teams() -> list[dict]:
    """List the teams on the platform and the services each team owns."""
    return platform.list_teams()


@mcp.tool(annotations=WRITE_NEEDS_APPROVAL)
def create_service(template: str, name: str, owner: str) -> dict:
    """Ask the platform to create a new service from a golden-path template
    (python-service or node-service) for a team. This does NOT create anything yet: it
    queues a request that a human must approve. Returns a request_id."""
    platform.validate_new_service(template, name, owner)
    request = approvals.create(
        "create_service", {"template": template, "name": name, "owner": owner}
    )
    return {
        "request_id": request["id"],
        "status": request["status"],
        "message": (
            "Not created yet. A human must approve this request "
            f"(request_id {request['id']}). Check progress with get_request_status."
        ),
    }


@mcp.tool(annotations=READ_ONLY)
def get_request_status(request_id: str) -> dict:
    """Status of a request made with create_service: pending_approval, approved or denied."""
    request = approvals.get(request_id)
    if request is None:
        raise platform.PlatformError(f"Unknown request '{request_id}'.")
    return request


# Plain HTTP health check (not MCP). App Service and Docker use it to know the app is alive.
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "version": __version__})


# Human side of the approval flow. Not an MCP tool: the agent cannot reach it. It needs
# ADMIN_TOKEN (set in the server's environment); with no token the endpoints do not exist.
def _admin_ok(request: Request) -> bool:
    token = os.environ.get("ADMIN_TOKEN", "")
    given = request.headers.get("authorization", "").removeprefix("Bearer ")
    return bool(token) and hmac.compare_digest(given, token)


@mcp.custom_route("/admin/approvals", methods=["GET"])
async def admin_list(request: Request) -> JSONResponse:
    if not os.environ.get("ADMIN_TOKEN"):
        return JSONResponse({"error": "not found"}, status_code=404)
    if not _admin_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return JSONResponse({"pending": approvals.pending()})


@mcp.custom_route("/admin/approvals/{request_id}/{decision}", methods=["POST"])
async def admin_decide(request: Request) -> JSONResponse:
    if not os.environ.get("ADMIN_TOKEN"):
        return JSONResponse({"error": "not found"}, status_code=404)
    if not _admin_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    decision = request.path_params["decision"]
    if decision not in ("approve", "deny"):
        return JSONResponse({"error": "use approve or deny"}, status_code=400)
    result = approvals.decide(request.path_params["request_id"], decision == "approve")
    if result is None:
        return JSONResponse({"error": "no pending request with that id"}, status_code=404)
    return JSONResponse(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="IDP MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run("stdio")
        return

    # stateless_http: every request stands alone, so the app can scale out and
    # restart (App Service) without losing client sessions.
    app = mcp.streamable_http_app(host=args.host, stateless_http=True, json_response=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
