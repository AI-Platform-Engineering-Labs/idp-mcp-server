# idp-mcp-server

**An MCP server that lets AI agents use your Internal Developer Platform (IDP) safely.**

Demo repo for the CNCG talk *"MCP Is the New API: Wiring AI Agents into Your Internal Developer Platform"*.

> **Status: scaffold.** The server runs, has a `hello` tool and the first real read-only tool
> (`list_services`), and deploys locally and to Azure. The rest of the demo is built step by step,
> see the [Roadmap](#roadmap).

---

## Contents

- [What this is (in one minute)](#what-this-is-in-one-minute)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Run it locally](#run-it-locally) (Docker Compose, Terraform, VS Code)
- [Deploy to Azure (KodeKloud sandbox)](#deploy-to-azure-kodekloud-sandbox)
- [CI](#ci)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)

---

## What this is (in one minute)

**MCP (Model Context Protocol)** is an open protocol for connecting AI agents to tools and data.
An MCP *server* publishes a list of **tools** (name, description, JSON input schema). An MCP
*client* (VS Code Copilot agent mode, Claude Desktop, Cursor, ...) reads that list, and the model
decides when to call a tool. The client sends a JSON-RPC `tools/call`, the server runs the code and
returns the result.

So, just as a REST API is how *programs* use your platform, an MCP server is how *agents* use it.
That's the "MCP is the new API" idea of the talk.

This repo's MCP server wraps a tiny pretend platform:

| Tool | Kind | What it does | Status |
|---|---|---|---|
| `hello` | read | Connection check | ✅ scaffold |
| `list_services` | read | Lists services from `server/catalog/services.yaml` | ✅ scaffold |
| `get_deploy_status` | read | Latest GitHub Actions run for a service | roadmap |
| `get_logs` | read | Recent logs of a deploy run | roadmap |
| `create_service` | **write** | Adds a service to the catalog / opens a PR | roadmap |
| `trigger_deploy` | **write** | Starts a deploy workflow | roadmap |

The interesting part of the talk is the **guardrails** around the write tools: read/write
separation, human approval, a least-privilege token, an audit log, and a prompt-injection demo.

---

## Architecture

```
             ┌──────────────────────────┐
             │  AI agent / MCP client   │   VS Code Copilot (agent mode), Claude Desktop, MCP Inspector
             └────────────┬─────────────┘
                          │ MCP (JSON-RPC)
        stdio (local)     │     Streamable HTTP  POST /mcp  (local Docker or Azure)
                          ▼
             ┌──────────────────────────┐
             │      idp-mcp-server       │   Python, official MCP SDK (server/idp_mcp)
             │                           │
             │  read tools   write tools │   write tools: approval + audit (roadmap)
             └──────┬───────────────┬────┘
                    │               │
          ┌─────────▼──────┐  ┌─────▼──────────────────┐
          │ Service catalog│  │ GitHub API             │   fine-grained, least-privilege token
          │ services.yaml  │  │ (Actions runs, PRs)    │   (roadmap)
          └────────────────┘  └────────────────────────┘
```

**One codebase, two transports.** The same tools are served two ways:

- **stdio**: the client starts the server as a child process and talks over stdin/stdout.
  Nothing listens on the network. Best for a single developer in VS Code.
- **Streamable HTTP**: the server listens on `http://HOST:PORT/mcp`. Use it for a shared server
  (a container, Azure App Service). The server runs *stateless*, so App Service can restart or
  scale it without breaking clients.

`GET /healthz` is a plain HTTP health check (not MCP) used by Docker and App Service.

**Three ways to run it, same code:**

| Where | How it's deployed | Transport | Cost |
|---|---|---|---|
| Laptop, quick | `docker compose up` | HTTP on `localhost:8000` | free |
| Laptop, "like prod" | Terraform + Docker provider (`infra/local`) | HTTP on `localhost:8000` | free |
| VS Code | VS Code runs `docker run -i` itself (`.vscode/mcp.json`) | stdio | free |
| Azure | Terraform + App Service, applied by GitHub Actions (`infra/azure`) | HTTPS `/mcp` | KodeKloud sandbox |

Using Terraform for *both* local and cloud means you rehearse the same `init / plan / apply /
destroy` loop at home that the pipeline runs in Azure. More detail in
[docs/architecture.md](docs/architecture.md).

---

## Repository layout

```
idp-mcp-server/
├── server/                      # the MCP server (this folder is what gets deployed to Azure)
│   ├── idp_mcp/
│   │   ├── server.py            # tools + /healthz + transport selection (stdio | http)
│   │   ├── catalog.py           # reads the service catalog
│   │   └── __main__.py          # `python -m idp_mcp`
│   ├── catalog/services.yaml    # the pretend platform's service catalog
│   ├── tests/                   # pytest: tools + health check
│   ├── requirements.txt         # runtime deps (pinned)
│   ├── requirements-dev.txt     # + pytest, ruff
│   └── pyproject.toml           # ruff + pytest config
├── infra/
│   ├── local/                   # Terraform: Docker provider builds the image and runs the container
│   └── azure/                   # Terraform: App Service plan + Linux web app in the sandbox RG
├── scripts/
│   ├── set-sandbox-secrets.sh   # start of each sandbox session: copy SP creds into GitHub secrets
│   ├── sandbox-down.sh          # end of session: delete those secrets
│   ├── tf-backend.sh            # (used by the workflow) creates the Terraform state storage account
│   └── smoke-test.sh            # curl /healthz and call list_services over MCP
├── .github/workflows/
│   ├── ci.yml                   # lint, tests, local Terraform apply + smoke test, terraform validate
│   └── deploy-azure.yml         # manual: terraform apply/destroy in Azure + deploy code + smoke test
├── .vscode/mcp.json             # VS Code MCP servers: stdio, local HTTP, Azure
├── docs/architecture.md         # deeper explanation of the design choices
├── Dockerfile                   # one image for compose, Terraform local and VS Code stdio
└── compose.yaml
```

---

## Prerequisites

Written for a **Windows laptop with Git Bash**. You do **not** need Python or the Azure CLI
locally: Python runs inside Docker, and Azure is driven from GitHub Actions.

| Tool | Needed for | Install (PowerShell) |
|---|---|---|
| Git + Git Bash | everything | already installed |
| GitHub CLI `gh` | sandbox secrets, running workflows | already installed; `gh auth login` |
| Docker Desktop | all local options | `winget install Docker.DockerDesktop` |
| Terraform ≥ 1.6 | `infra/local` only | `winget install Hashicorp.Terraform` |
| VS Code + GitHub Copilot | the agent demo | `winget install Microsoft.VisualStudioCode` |
| KodeKloud account | Azure sandbox | kodekloud.com → Cloud Playgrounds → Azure |

Optional: [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
(`npx @modelcontextprotocol/inspector`, needs Node) to click through tools without an AI model.

---

## Run it locally

Clone first:

```bash
git clone https://github.com/AI-Platform-Engineering-Labs/idp-mcp-server.git
cd idp-mcp-server
```

### Option A: Docker Compose (fastest)

```bash
docker compose up --build -d
bash scripts/smoke-test.sh            # health check + calls list_services over MCP
docker compose down
```

### Option B: Terraform with the Docker provider (same workflow as the cloud)

`infra/local` uses the [kreuzwerker/docker](https://registry.terraform.io/providers/kreuzwerker/docker/latest)
provider. `terraform apply` builds the image from the `Dockerfile` and starts the container on
`127.0.0.1:8000`. When you change server code, the next `apply` rebuilds the image (Terraform
hashes the source files).

```bash
cd infra/local
cp terraform.tfvars.example terraform.tfvars   # on Windows this sets docker_host to Docker Desktop's pipe
terraform init
terraform plan
terraform apply                                # type yes
bash ../../scripts/smoke-test.sh
terraform destroy                              # when done
```

On Linux or macOS you can skip `terraform.tfvars`; the provider finds the Docker socket itself.

### Option C: VS Code over stdio (how the agent demo runs)

1. Build the image once: `docker build -t idp-mcp-server:local .`
2. Open the repo in VS Code. `.vscode/mcp.json` already defines three servers.
3. Command palette → **MCP: List Servers** → `idp-local-stdio` → **Start**.
4. Open Copilot Chat in **Agent** mode, check the tools icon shows `hello` and `list_services`,
   and ask: *"Which services does team-payments own?"*

`idp-local-http` connects to a server that's already running (Option A or B) instead.
`idp-azure` asks for your Azure URL and connects to the cloud deployment.

### Running the tests

CI runs them on every PR. To run them yourself without Python installed:

```bash
docker run --rm -v "$PWD/server:/src" -w /src python:3.12-slim \
  sh -c "pip install -q -r requirements-dev.txt && ruff check . && pytest -q"
```

(In Git Bash, if the volume path is mangled, prefix the command with `MSYS_NO_PATHCONV=1`.)

---

## Deploy to Azure (KodeKloud sandbox)

### What the sandbox allows, and how this repo deals with it

| Sandbox rule | What the code does |
|---|---|
| Sessions last **2 hours**, then everything is deleted | Deploy is one workflow run (~5 min). Names get a random suffix, nothing depends on an earlier session. |
| One **pre-created resource group** (`kml_rg_main_...`); you can't create one | Terraform reads it with a `data` source, never creates one. |
| Only some **SKUs/regions** | App Service plan **B1** (F1 also allowed), region = the resource group's region. |
| Service principal with a **client secret**; no OIDC/federated credentials, no role assignments | The workflow logs in with the secret, stored as GitHub secrets for that session only. |
| SP can't register resource providers | `resource_provider_registrations = "none"` in the provider. |
| ACR builds are blocked | App Service runs the Python code directly (built-in Python 3.12 stack), not a container image. |

Terraform **state** lives in a storage account inside the same resource group.
`scripts/tf-backend.sh` creates it on the first run of each session. When the sandbox expires,
the state goes with the resources, which is what you want here.

### One-time setup in GitHub

1. Repo **Settings → Environments → New environment** named `sandbox`. Add yourself under
   **Required reviewers** to get an approval step before Terraform changes anything (optional
   but good practice, and it's a guardrail you can show in the talk).

### Every sandbox session

1. On KodeKloud, start the **Azure Playground**. Copy the service principal details
   (client ID, client secret, tenant ID, subscription ID) and the resource group name.
2. In Git Bash, from the repo folder:

   ```bash
   export ARM_CLIENT_ID=...  ARM_CLIENT_SECRET=...  ARM_TENANT_ID=...
   export ARM_SUBSCRIPTION_ID=...  RESOURCE_GROUP=kml_rg_main_...
   bash scripts/set-sandbox-secrets.sh
   ```

   This stores them as repo secrets plus a `RESOURCE_GROUP` variable, using only `gh`.
3. Deploy:

   ```bash
   gh workflow run deploy-azure -f action=apply
   gh run watch
   ```

   (or **Actions → deploy-azure → Run workflow**). Approve the `sandbox` environment if you set
   it up. The workflow:
   1. logs in to Azure with the sandbox service principal,
   2. creates the state storage account if needed (`tf-backend.sh`),
   3. `terraform plan` (shown in the run summary) then `terraform apply`,
   4. zips `server/` and deploys it to the web app (App Service runs `pip install`),
   5. waits for `/healthz` and calls `list_services` over MCP.
4. The run summary shows the URL. The MCP endpoint is `https://<app>.azurewebsites.net/mcp`.
   Test it with `bash scripts/smoke-test.sh https://<app>.azurewebsites.net` or connect
   `idp-azure` in VS Code.
5. When done: `gh workflow run deploy-azure -f action=destroy` (optional, the sandbox cleans up
   anyway) and `bash scripts/sandbox-down.sh` to remove the expired secrets.

### What gets created

| Resource | Name | Notes |
|---|---|---|
| App Service plan | `idpmcp-plan-<suffix>` | Linux, B1 |
| Linux Web App | `idpmcp-<suffix>` | Python 3.12, HTTPS only, TLS 1.2, FTPS off, health check `/healthz` |
| Storage account | `tfidp<hash>` | Terraform state only, created by the script, not by Terraform |

> **Security note for the scaffold:** the Azure endpoint is public and has no authentication yet.
> That's acceptable while it only serves the read-only demo catalog, and adding auth is roadmap
> step 5. Don't put real data behind it before then.

---

## CI

`.github/workflows/ci.yml` runs on every PR and push to `main`:

| Job | What it proves |
|---|---|
| `server (lint + test)` | ruff lint/format and pytest pass |
| `local stack` | `terraform apply` in `infra/local` builds and runs the container; MCP works over HTTP and stdio |
| `terraform (local)`, `terraform (azure)` | both stacks are formatted (`terraform fmt`) and valid (`terraform validate`) |

Azure deploys are **manual** (`deploy-azure.yml`), because sandbox credentials only exist during
a session.

---

## Roadmap

The demo is built in small steps, each a PR that keeps CI green.

| # | Step | Talk point |
|---|---|---|
| 0 | **Scaffold** (this PR): layout, hello-world server, `list_services`, Docker, Terraform local + Azure, CI | "An MCP server is just a small service" |
| 1 | Read tools on the catalog: richer `list_services`, `get_service`; MCP **resources** for the catalog file | Tools vs resources |
| 2 | GitHub-backed read tools: `get_deploy_status`, `get_logs` using a **fine-grained, read-only token** | The platform API behind the tools |
| 3 | Write tools: `create_service` (opens a PR), `trigger_deploy` (dispatches a workflow), in a separate write toolset | Read/write separation |
| 4 | **Human approval** for write tools (MCP elicitation / client confirmation) and a dry-run mode | Human in the loop |
| 5 | **Auth** on the HTTP endpoint (bearer token in App Service settings), token scopes per toolset | Least privilege |
| 6 | **Audit log**: every tool call (who, tool, args, result) as structured JSON to App Service logs | Accountability |
| 7 | **Prompt-injection demo**: a malicious service description tries to make the agent call `trigger_deploy`; show the guardrails stopping it | Why the guardrails exist |
| 8 | Talk polish: demo script, reset script, slides | |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `terraform apply` in `infra/local` says it can't reach the Docker daemon | Start Docker Desktop; on Windows set `docker_host = "npipe:////./pipe/docker_engine"` in `terraform.tfvars`. |
| Port 8000 already in use | Stop the other run (`docker compose down` or `terraform destroy`), or set `host_port = 8001`. |
| VS Code `idp-local-stdio` fails to start | Build the image first: `docker build -t idp-mcp-server:local .` |
| Workflow fails at "Check sandbox secrets" | Run `scripts/set-sandbox-secrets.sh` for this session; old session secrets don't work. |
| Azure `/healthz` never becomes healthy | First start takes a few minutes while App Service installs packages. Check **Log stream** in the portal. |
| `terraform apply` in Azure fails with a SKU/region policy error | Keep `sku = "B1"` and leave `location` empty so it uses the resource group's region. |
