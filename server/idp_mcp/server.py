"""The MCP server.

Read-only tools for now: hello, list_services, call_service. They talk to the IDP
(Backstage) through idp_mcp.platform. Write tools come later (see the roadmap in README.md).

Two transports, same tools:
  * stdio            -> a local client (VS Code, Claude Desktop) starts this process itself
  * streamable-http  -> the server listens on http://HOST:PORT/mcp (Docker, Azure App Service)
"""

import argparse
import os

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from idp_mcp import __version__, platform

mcp = MCPServer(
    name="idp-mcp-server",
    version=__version__,
    instructions=(
        "Tools for the Internal Developer Platform. Read-only tools are safe to call. "
        "Write tools (added later) need human approval."
    ),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


@mcp.tool(annotations=READ_ONLY)
def hello(name: str = "platform engineer") -> str:
    """Say hello. Use this to check the MCP connection works end to end."""
    return f"Hello, {name}! idp-mcp-server {__version__} is up."


@mcp.tool(annotations=READ_ONLY)
def list_services(owner: str | None = None) -> list[dict]:
    """List services in the platform's software catalog (Backstage), optionally filtered
    by owning team, e.g. owner="team-payments". Each service has ai_access: "open" means
    you may call it, "guarded" means it is off limits to agents."""
    services = platform.list_services()
    if owner:
        services = [s for s in services if s.get("owner") == owner]
    return services


# The services have no public address: this goes through the IDP's proxy.
CALL_SERVICE = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)


@mcp.tool(annotations=CALL_SERVICE)
def call_service(name: str, path: str = "/") -> dict:
    """Send a GET request to a platform service through the IDP (Backstage proxy) and
    return the HTTP status and response body. Only services with ai_access "open" can be
    called; guarded ones are refused. Use list_services to find valid names."""
    return platform.call_service(name, path)


# Plain HTTP health check (not MCP). App Service and Docker use it to know the app is alive.
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "version": __version__})


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
