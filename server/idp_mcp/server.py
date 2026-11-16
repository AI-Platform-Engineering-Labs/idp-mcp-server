"""The MCP server.

Scaffold stage: one hello-world tool and the first read-only tool (list_services).
The rest of the IDP tools are added step by step (see the roadmap in README.md).

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

from idp_mcp import __version__
from idp_mcp.catalog import load_services

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
    """List services in the platform catalog, optionally filtered by owning team."""
    services = load_services()
    if owner:
        services = [s for s in services if s.get("owner") == owner]
    return services


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
