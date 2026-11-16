# Architecture and design choices

This page explains *why* the demo looks the way it does, so you can explain it on stage.

## The three layers

| Layer | Component | Job |
|---|---|---|
| Agent | VS Code Copilot / Claude | Decides which tool to call, based on tool descriptions |
| Agent gateway | **MCP server** (`server/`) | Turns IDP capabilities into a small set of well-described, guarded tools |
| Platform | **Backstage** (`backstage/`) + services | Knows what exists, who owns it, and is the only door to the services |

The MCP server holds no knowledge of its own: ask it for services and it asks Backstage. That is
deliberate. The IDP stays the source of truth, and the MCP server is a thin, auditable layer whose
whole purpose is *what an agent may do*.

## How an MCP call flows

1. The client connects and sends `initialize`. The server answers with its name, version,
   capabilities and `instructions` (a hint to the model about how to use the tools).
2. The client sends `tools/list`. Each tool comes back with a name, a description (the docstring)
   and a JSON schema built from the Python type hints. **The description is what the model reads
   to decide when to call the tool**, so it is part of your API design.
3. When the model wants a tool, the client sends `tools/call`. The server validates the arguments,
   runs the function and returns content plus structured output.

You can watch this with curl, which is what `scripts/smoke-test.sh` does:

```bash
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Guardrails already in place

| Guardrail | Where | How |
|---|---|---|
| Services reachable **only via the IDP** | `k8s/network-policy.yaml`, `k8s/services.yaml` | Services are `ClusterIP` (no public IP). A NetworkPolicy, enforced by Cilium on AKS, lets only Backstage pods in. The deploy workflow proves a direct call is blocked. |
| **Least-privilege token** for the MCP server | `backstage/app-config.yaml` → `backend.auth.externalAccess` | A static token whose `accessRestrictions` allow only the `catalog` and `proxy` plugins. Checked locally: catalog 200, proxy 200, search 403, scaffolder 403, no token 401. |
| **Only catalog services** can be called | `server/idp_mcp/platform.py` | `call_service` checks the name against the catalog and rejects paths with `..`, `//` or no leading `/`. No URL from the model is ever fetched directly. |
| **Read-only** tool hints | `server/idp_mcp/server.py` | `ToolAnnotations(readOnlyHint=True)`. Clients can skip confirmation for these. Write tools (roadmap) will be `destructiveHint=True`. Hints are advisory, so enforcement stays on the server side. |
| **Errors the agent can read** | `PlatformError(ToolError)` | Expected failures (unknown service, Backstage down) become a clear `isError` result; unexpected crashes are logged but their details are not shown to the model. |
| No cluster credentials for the agent | the whole design | The MCP server pod has no Kubernetes service account token (`automountServiceAccountToken: false`). |

## Backstage choices

- Generated with `npx @backstage/create-app` (Backstage 1.56, new frontend system). Kept close to
  the template so it's easy to upgrade, with these changes:
  - `catalog/`: our org (teams) and the `shop` system with its services.
  - `proxy.endpoints./svc/<name>`: one endpoint per service. The proxy requires a Backstage token
    by default (`credentials: require`), so anonymous callers get 401.
  - `backend.auth.externalAccess`: the MCP server's token, described above.
  - Production config: base URL from `BACKSTAGE_BASE_URL`, **in-memory SQLite** (the catalog is
    re-read from files on start, so no PostgreSQL to run), **guest sign-in** (demo only).
  - `packages/backend/src/index.ts`: the PostgreSQL search module removed (in-memory Lunr instead).
- The `Dockerfile` builds everything inside Docker (multi-stage), so no Node.js on the laptop, and
  it avoids BuildKit-only syntax so Terraform's Docker provider can build it too.

## Kubernetes (k8s/)

- One namespace `idp`. Backstage and the MCP server have `LoadBalancer` services (public IPs on
  AKS); the three services are `ClusterIP`.
- Same host names everywhere (`backstage`, `payments-api`, ...), so the same Backstage config
  works in Kubernetes and in Docker.
- All pods run as non-root, no privilege escalation, all capabilities dropped.
- The MCP↔Backstage token is a Kubernetes Secret created by the workflow (`openssl rand`), never
  stored in git.

## Azure (infra/azure)

- `data "azurerm_resource_group"`: the playground gives one resource group and forbids creating
  others, so it's read, not managed. AKS still creates its own `MC_...` node resource group.
- AKS: 2 × `Standard_D2s_v3` (the playground's only allowed size), Free tier, ephemeral OS disk
  (no Premium managed disk), Azure CNI overlay with the **Cilium** data plane and network policy.
- No monitoring add-on (the playground requires alerting off) and no role assignments (blocked),
  which is why images come from public GHCR instead of an attached ACR.

## Why Terraform runs in GitHub Actions, not on the laptop

- No Azure CLI, kubectl or Python needed locally.
- Playground credentials live only in GitHub secrets, not in a shell history.
- The `sandbox` environment's required reviewer gives a human approval before any change: the
  same "human in the loop" idea the talk applies to AI agents.
