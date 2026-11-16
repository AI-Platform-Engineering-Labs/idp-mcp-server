# Architecture and design choices

This page explains *why* the scaffold looks the way it does, so you can explain it on stage.

## How an MCP call flows

1. The client connects and sends `initialize`. The server answers with its name, version,
   capabilities and `instructions` (a hint to the model about how to use the tools).
2. The client sends `tools/list`. Each tool comes back with a name, a description (the docstring)
   and a JSON schema built from the Python type hints. **The description is what the model reads
   to decide when to call the tool**, so it is part of your API design.
3. When the model wants a tool, the client sends `tools/call` with arguments. The server validates
   them against the schema, runs the function and returns content (text) plus structured output.

You can watch this with nothing but curl, which is what `scripts/smoke-test.sh` does:

```bash
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Code (server/idp_mcp/server.py)

- Uses the **official MCP Python SDK** (`mcp` 2.x, `MCPServer` class, formerly `FastMCP`).
  A tool is a decorated Python function: `@mcp.tool()`.
- Read-only tools carry `ToolAnnotations(readOnlyHint=True, destructiveHint=False)`. Clients use
  these hints, for example to skip confirmation for safe tools. Write tools (roadmap) will be
  marked `destructiveHint=True`. Hints are advisory, so real enforcement happens on the server
  (approval, token scopes).
- `--transport stdio|http` picks the transport. HTTP mode builds a Starlette app with
  `streamable_http_app(stateless_http=True, json_response=True)` and serves it with uvicorn:
  - *stateless*: no server-side session, so a restart or second instance doesn't break clients;
  - *json_response*: plain JSON replies instead of an SSE stream, simple to curl and to debug.
- `/healthz` is a `custom_route`, plain HTTP outside MCP.

## Local deployment (infra/local)

- Terraform with the `kreuzwerker/docker` provider. Two resources: `docker_image` (builds the
  repo's `Dockerfile`) and `docker_container` (runs it, port bound to `127.0.0.1` only).
- A hash of the source files is a `trigger` on the image, so code changes rebuild on `apply`.
- State is a local file. Nothing to set up, nothing to pay.

## Cloud deployment (infra/azure)

- `data "azurerm_resource_group"`: the sandbox gives you one resource group and forbids creating
  others, so it's read, not managed.
- `azurerm_service_plan` (Linux, B1) + `azurerm_linux_web_app` with the built-in Python 3.12
  stack and the startup command `python -m idp_mcp --transport http --port 8000`.
- Code, not container: the sandbox blocks ACR builds and a public registry image would need extra
  setup, so the workflow zip-deploys `server/` and App Service installs `requirements.txt`
  (`SCM_DO_BUILD_DURING_DEPLOYMENT=true`).
- Hardening that costs nothing: HTTPS only, TLS 1.2 minimum, FTPS disabled, health check with
  eviction, HTTP logs kept 3 days.
- State backend `azurerm` with partial config: the workflow passes the storage account at
  `terraform init` time, because its name depends on the session's subscription and resource group.

## Why Terraform runs in GitHub Actions, not on the laptop

- No Azure CLI or Python needed locally.
- Sandbox credentials live only in GitHub secrets for the session, not in a shell history.
- The `sandbox` environment's required reviewer gives a human approval before any change: the
  same "human in the loop" idea the talk applies to AI agents.
