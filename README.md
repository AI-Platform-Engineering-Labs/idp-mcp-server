# idp-mcp-server

**AI agents using your Internal Developer Platform (IDP) through MCP, safely.**

A **Backstage** portal and three sample services run on **AKS** (or Docker on your laptop). The
services have no public address: the IDP is the only way in. An **MCP server** gives AI agents
(GitHub Copilot, Claude) tools to use the IDP: list the services in the catalog, and call a
service through Backstage.

---

## Contents

- [What this is (in one minute)](#what-this-is-in-one-minute)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Run it locally](#run-it-locally)
- [Deploy to Azure AKS (KodeKloud playground)](#deploy-to-azure-aks-kodekloud-playground)
- [Connect an AI client](#connect-an-ai-client)
- [CI and images](#ci-and-images)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)

---

## What this is (in one minute)

**An IDP** (Internal Developer Platform) is how a company's developers find, create and run
services without filing tickets. **Backstage** is the most common open-source IDP portal: its
*software catalog* lists every service, who owns it and what it depends on.

**MCP (Model Context Protocol)** is an open protocol for connecting AI agents to tools. An MCP
*server* publishes **tools** (name, description, input schema). An MCP *client* (VS Code Copilot
agent mode, Claude Desktop, Claude Code, ...) shows them to the model, and the model decides when
to call one.

So, just as a REST API is how *programs* use your platform, an MCP server is how *agents* use it.
That's the "MCP is the new API" idea of the talk.

| Tool | Kind | What it does | Status |
|---|---|---|---|
| `hello` | read | Connection check | ✅ |
| `list_services` | read | Lists services from the **Backstage catalog** (optionally by owner) | ✅ |
| `get_service` | read | One service's owner, tier, lifecycle, tags and links | ✅ |
| `get_service_status` | read | Is it healthy? The platform checks it through the Backstage proxy and returns only healthy/unhealthy, never the service's data | ✅ |
| `list_teams` | read | Teams and the services each owns | ✅ |
| `search_docs`, `get_doc` | read | Search and read the internal knowledge base (21 fictional how-tos, golden paths, standards, onboarding, runbooks in `backstage/catalog/docs/docs`) | ✅ |
| `list_templates` | read | The software templates (golden paths) from Backstage | ✅ |
| `create_service` | **write, needs a human** | Ask for a new service from a golden-path template. Only **queues a request**: nothing is created until a human approves | ✅ (the action itself is a placeholder) |
| `get_request_status` | read | Pending, approved or denied | ✅ |
| `get_deploy_status`, `get_logs`, `trigger_deploy` | read / write | Deploy runs, logs, start a deploy (GitHub Actions) | roadmap |

The tools are **platform actions** (find a service, check it, ask for a new one), not a back door
to the business services themselves: the agent cannot send requests to `payments-api`.

The interesting part of the talk is the **guardrails**: read/write separation, least-privilege
tokens, services reachable only via the IDP, human approval for write tools, an audit log, and a
prompt-injection demo.

---

## Architecture

```
   your laptop                                   AKS cluster (namespace "idp")  /  local Docker network "idp"
 ┌──────────────────┐                          ┌──────────────────────────────────────────────────────────────┐
 │ VS Code Copilot  │   MCP over HTTP          │  ┌──────────────┐  catalog API + proxy  ┌──────────────────┐ │
 │ Claude Desktop   │ ───────────────────────▶ │  │  MCP server  │ ────────────────────▶ │    Backstage     │ │
 │ (the AI agent)   │   http://<ip>/mcp        │  │ (Python, MCP │  Bearer token, valid  │   (IDP portal)   │ │
 └──────────────────┘                          │  │  SDK)        │  for catalog + proxy  │  catalog: shop   │ │
                                               │  └──────────────┘  plugins only         └────────┬─────────┘ │
 ┌──────────────────┐   browser                │       public (LoadBalancer)        public (LB)  │ /api/proxy │
 │ you / audience   │ ───────────────────────────────────────────────────────────────▶          │  /svc/<name>│
 └──────────────────┘   http://<ip>            │                                                 ▼            │
                                               │   ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
                                               │   │ payments-api │ │  orders-web  │ │ notifications-worker │ │  (+ customers-api)
                                               │   └──────────────┘ └──────────────┘ └──────────────────────┘ │
                                               │   ClusterIP only, NetworkPolicy: ingress from Backstage only  │
                                               └──────────────────────────────────────────────────────────────┘
```

**How a request flows**, e.g. you ask Copilot *"Is the payments API healthy?"*:

1. Copilot sees the MCP tools and calls `get_service_status(name="payments-api")`.
2. The MCP server checks the name against the catalog, then calls
   `GET http://backstage:7007/api/proxy/svc/payments-api/` with its token.
3. Backstage accepts the token only for the `catalog` and `proxy` plugins, and forwards the call
   to `payments-api` inside the cluster.
4. `payments-api` accepts it because it comes from a Backstage pod (NetworkPolicy). A direct call
   from anywhere else, including the MCP server's pod, is dropped.
5. The MCP server returns only `healthy: true` and the HTTP status. The service's own response
   never reaches the agent.

**And a write**, e.g. *"Create a python service called pay-gateway for team-payments"*:
`create_service` validates the request (known template and team, unused name) and **queues it**.
The agent is told "not created yet, a human must approve". You approve with
`bash scripts/approve.sh approve <request-id>`; the agent cannot, because approval is an admin
endpoint outside MCP that needs a token the agent never sees.

**Why this shape?** The agent never gets a key to the cluster or to the services. Everything goes
through the IDP, which already knows who owns what and enforces access. That's the core
guardrail, and the later steps (approval, audit, injection) build on it.

**The pieces:**

| Piece | Where | Notes |
|---|---|---|
| Backstage | `backstage/` | Created with `@backstage/create-app` (Backstage 1.56). Changes: catalog in `backstage/catalog/`, proxy endpoints `/svc/<name>`, a static token for the MCP server, in-memory SQLite, guest sign-in. |
| MCP server | `server/` | Python, official MCP SDK (`mcp` 2.x). Talks to Backstage in `server/idp_mcp/platform.py`. Without `BACKSTAGE_URL` it falls back to `server/catalog/services.yaml` (unit tests, standalone runs). |
| Sample services | `k8s/services.yaml` | `hashicorp/http-echo` returning a small JSON status, standing in for real apps. |
| Cluster config | `k8s/` | Kustomize: Deployments, Services, NetworkPolicy, all in namespace `idp`. |
| Azure infra | `infra/azure/` | Terraform: one AKS cluster (2 × Standard_D2s_v3, Cilium network policy). |
| Local infra | `infra/local/` and `compose.yaml` | The same containers on Docker, via Terraform or docker compose. |

> **Did you know?** New Backstage apps ship with Backstage's own MCP plugin
> (`@backstage/plugin-mcp-actions-backend`, endpoint `/api/mcp-actions/v1`), which exposes
> Backstage "actions" as MCP tools. This repo's MCP server is a separate, purpose-built server
> so we control exactly which tools exist and what guardrails wrap them. That contrast is a
> good talking point.

More detail in [docs/architecture.md](docs/architecture.md).

---

## Repository layout

```
idp-mcp-server/
├── server/                      # the MCP server (Python)
│   ├── idp_mcp/
│   │   ├── server.py            # tools + /healthz + transport selection (stdio | http)
│   │   ├── platform.py          # talks to Backstage: catalog API + proxy, with the token
│   │   └── catalog.py           # fallback catalog file loader
│   ├── catalog/services.yaml    # fallback catalog (tests, standalone)
│   └── tests/                   # pytest, Backstage faked
├── backstage/                   # the IDP portal (Backstage app)
│   ├── catalog/                 # the software catalog: system "shop", services, teams
│   ├── app-config.yaml          # proxy endpoints, MCP token rules, catalog locations
│   ├── app-config.production.yaml  # container settings (URL from env, SQLite, guest)
│   ├── packages/app, packages/backend   # generated by create-app (backend: pg search removed)
│   └── Dockerfile               # builds everything inside Docker, no Node.js needed locally
├── k8s/                         # what runs on the cluster (kubectl apply -k k8s/)
├── infra/
│   ├── azure/                   # Terraform: AKS in the KodeKloud playground resource group
│   └── local/                   # Terraform: the whole stack on your laptop's Docker
├── scripts/
│   ├── azure-login.sh           # (workflow) login + find the playground's subscription and RG
│   ├── tf-backend.sh            # (workflow) Terraform state storage account
│   ├── smoke-test.sh            # calls the MCP server like an agent would: health, list, call
│   ├── set-sandbox-secrets.sh   # optional: set the 3 playground secrets with gh
│   └── sandbox-down.sh          # optional: delete them afterwards
├── .github/workflows/
│   ├── ci.yml                   # tests, full local stack in Docker, Terraform + k8s validation
│   ├── images.yml               # build + publish both images to GHCR on merge to main
│   └── deploy-azure.yml         # manual: AKS + deploy + smoke test (or destroy)
├── .vscode/mcp.json             # VS Code MCP servers: local stdio, local HTTP, AKS
├── compose.yaml                 # the whole stack with docker compose
└── Dockerfile                   # MCP server image
```

---

## Prerequisites

Written for a **Windows laptop with Git Bash**. You do **not** need Node.js, Python or the Azure
CLI: everything builds in Docker, and Azure is driven from GitHub Actions.

| Tool | Needed for | Install (PowerShell) |
|---|---|---|
| Git + Git Bash, GitHub CLI `gh` | everything | already installed; `gh auth login` |
| Docker Desktop (give it ≥ 6 GB RAM) | local stack | `winget install Docker.DockerDesktop` |
| Terraform ≥ 1.6 | `infra/local` | `winget install Hashicorp.Terraform` |
| VS Code + GitHub Copilot | the agent demo | `winget install Microsoft.VisualStudioCode` |
| kubectl (optional) | poking at AKS from your laptop | `winget install Kubernetes.kubectl` |
| KodeKloud account | Azure playground | kodekloud.com → Cloud Playgrounds → Azure |

---

## Run it locally

```bash
git clone https://github.com/AI-Platform-Engineering-Labs/idp-mcp-server.git
cd idp-mcp-server
```

### Option A: Terraform with the Docker provider (same workflow as the cloud)

`infra/local` starts five containers on a private Docker network `idp`: Backstage, the MCP
server and the three services. Only Backstage (port 7007) and the MCP server (port 8000) are
published, on `127.0.0.1`.

```bash
cd infra/local
terraform init
terraform apply                                # type yes
```

Terraform finds Docker Desktop by itself in most cases, so no variables are needed. If you get a
Docker connection error, see [Troubleshooting](#troubleshooting) (the fix depends on your OS).

By default it **pulls the published images** from GHCR (`image_source = "ghcr"`), which takes a
minute. To build from your checkout instead, set `image_source = "build"` (Backstage takes
10-15 minutes the first time; on an Apple Silicon Mac `docker compose up --build` is faster
because it builds natively).

Backstage needs about a minute to start. Then:

```bash
ADMIN_TOKEN=local-admin-token bash ../../scripts/smoke-test.sh   # read tools, queued write, human approval
```

Open **http://localhost:7007** (click *Enter* as guest) to see the catalog. When done:
`terraform destroy`.

### Option B: docker compose

```bash
docker compose up --build -d         # first Backstage build: 10-15 minutes
bash scripts/smoke-test.sh
docker compose down
```

### Running the tests

CI runs them on every PR. Without Python installed:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD/server:/src" -w /src python:3.12-slim \
  sh -c "pip install -q -r requirements-dev.txt && ruff check . && pytest -q"
```

---

## Deploy to Azure AKS (KodeKloud playground)

> **Step-by-step runbook** with every value, where to get it, the demo script, a "real world" comparison
> and troubleshooting: **[docs/runbook-aks.md](docs/runbook-aks.md)**.

### What the playground allows, and how this repo deals with it

From [kodekloud.com/cloud-playgrounds/azure](https://kodekloud.com/cloud-playgrounds/azure):

| Playground rule | What the code does |
|---|---|
| AKS: **1 node pool, max 2 nodes, Standard_D2s_v3 only**; alerting must be disabled | `node_count = 2`, `Standard_D2s_v3`, no monitoring add-on. 2 × (2 vCPU, 8 GB) is plenty. |
| **Premium disks not allowed** | Nodes use an **ephemeral OS disk** (48 GB on the VM's cache), so no managed disk at all. |
| One **pre-created resource group**; you can't create one | Terraform reads it with a `data` source. AKS puts nodes and IPs in its own `MC_...` group. |
| **No role assignments**, no OIDC | No ACR attach: images come from **public GHCR**. Login uses the service principal secret. |
| **ACR task runs blocked** | Images are built in GitHub Actions (`images.yml`), not in Azure. |
| Max **3 load balancers** per session | AKS uses one Standard LB with two public IPs (Backstage, MCP server). |
| US regions only; sessions are short-lived | Region = the resource group's. Deploy is one workflow run; nothing depends on an earlier session. |

### One-time setup

1. **Images**: after merging to `main`, the `images` workflow publishes
   `ghcr.io/ai-platform-engineering-labs/idp-backstage` and `.../idp-mcp-server`. Make both
   **public** once: GitHub org → **Packages** → each package → **Package settings** →
   **Change visibility** → Public. (AKS can't use a registry password in the playground setup
   we chose, and the workflows check this for you.)
2. **Optional approval gate**: repo **Settings → Environments → New environment** `sandbox`,
   add yourself as **Required reviewer**. Terraform then waits for your click, a nice
   "human in the loop" moment to show in the talk.

### Every new playground: update 3 secrets, click Run

1. On KodeKloud, start the **Azure Playground** and keep its page open.
2. In GitHub: **Settings → Secrets and variables → Actions → Repository secrets**. Update:

   | Secret | Value from the playground page |
   |---|---|
   | `ARM_CLIENT_ID` | Application (client) ID |
   | `ARM_CLIENT_SECRET` | Client secret |
   | `ARM_TENANT_ID` | Tenant (directory) ID |

   (Or from Git Bash: `export ARM_CLIENT_ID=... ARM_CLIENT_SECRET=... ARM_TENANT_ID=...` then
   `bash scripts/set-sandbox-secrets.sh`.)
3. **Actions → deploy-azure → Run workflow**: first `action: preflight` (read-only checks, 1 minute),
   then `action: apply`. Or `gh workflow run deploy-azure -f action=preflight`, then
   `gh workflow run deploy-azure -f action=apply && gh run watch`.

The run takes about **12-15 minutes**:

1. checks the GHCR images are pullable,
2. logs in and **finds the subscription and `kml_rg_main_*` resource group itself**,
3. Terraform creates the AKS cluster (~6-8 min),
4. applies `k8s/` with the image tag, creates the MCP↔Backstage token as a Kubernetes secret,
5. waits for the two public IPs and tells Backstage its URL,
6. runs `smoke-test.sh` against the MCP server (list + call through Backstage),
7. proves a direct call to `payments-api` from a non-Backstage pod is **blocked**,
8. prints the **Backstage URL** and **MCP endpoint** in the run summary.

To remove everything early: run the workflow with `action: destroy` (the playground also cleans
up when it expires).

**Look around with kubectl** (optional, needs Azure CLI or Cloud Shell in the portal):
`az aks get-credentials -g <rg> -n <cluster>` then `kubectl -n idp get pods,svc`.

> **Security note:** the MCP endpoint and Backstage are public and Backstage uses guest sign-in.
> Fine for a short-lived demo with fake services; roadmap steps add auth on the MCP endpoint.
> Don't point this at real systems as is.

---

## Connect an AI client

**VS Code (GitHub Copilot, agent mode)**: `.vscode/mcp.json` defines three servers. Command
palette → **MCP: List Servers** → pick one → **Start**:

| Server | Use when |
|---|---|
| `idp-local-http` | the local stack is running (Option A or B) |
| `idp-local-stdio` | same, but VS Code starts its own MCP server container over stdio (`docker build -t idp-mcp-server:local .` first) |
| `idp-aks` | after a deploy; paste the MCP endpoint from the run summary, e.g. `http://20.1.2.3/mcp` |

Then in Copilot Chat (Agent mode) try:

- *"Which teams exist and what does each own?"* → `list_teams`
- *"Who owns payments-api, who is on call, and what breaks if it goes down?"* → `get_service`
- Incident demo: `docker stop payments-api`, then *"Checkout is failing. What is down, who owns it, and what is affected?"* (`docker start payments-api` to fix; see `docs/demo-local.md`)
- *"Check whether every service in the shop system is healthy."* → `list_services` + `get_service_status` per service
- *"Create a python-service called pay-gateway for team-payments."* → queued, **not created**
- Then in a terminal: `bash scripts/approve.sh list`, then `bash scripts/approve.sh approve <id>`
- *"What happened to my request?"* → `get_request_status` now says approved

### The guardrails in this demo

| Guardrail | Where |
|---|---|
| Read and write are separate tools; write tools are marked destructive | `server/idp_mcp/server.py` |
| A write tool only **queues** a request; a human approves outside MCP | `server/idp_mcp/approvals.py`, `scripts/approve.sh`, admin endpoint needs `ADMIN_TOKEN` |
| Agent gets only healthy/unhealthy for a service, never its data or a caller-chosen URL | `platform.get_service_status` |
| Agent can only ask for golden-path templates, known teams, unused names | `platform.validate_new_service` |
| MCP token limited to the catalog and proxy plugins | `backstage/app-config.yaml` |
| Services unreachable except through Backstage | `k8s/network-policy.yaml` |

The approval store is in memory and the "create" action is a placeholder: the flow is real, but
no repository is created. `scripts/smoke-test.sh` proves it end to end.

**Claude Desktop / Claude Code**: add an HTTP MCP server with the same URL
(Claude Code: `claude mcp add --transport http idp http://localhost:8000/mcp`).

**On stage:** `docs/demo-local.md` is a one-page cheat sheet.

**No AI at all**: `bash scripts/smoke-test.sh <base-url>` makes the same MCP calls with curl.

---

## CI and images

| Workflow | When | What it proves |
|---|---|---|
| `ci.yml` → `server` | every PR | ruff + pytest |
| `ci.yml` → `local stack` | every PR | builds both images, `terraform apply` in `infra/local`, MCP → Backstage → service works end to end, services are not published, stdio works |
| `ci.yml` → `kubernetes manifests` | every PR | `k8s/` renders and passes schema validation (kubeconform) |
| `ci.yml` → `terraform (local/azure)` | every PR | `terraform fmt` + `validate` |
| `ci.yml` → `multi-arch build` | every PR | both images also build for **arm64** (Apple Silicon Macs) |
| `images.yml` | merge to `main` | publishes `:latest` and `:<sha>` to GHCR for **amd64 + arm64**, warns if a package isn't public |
| `deploy-azure.yml` | manual | AKS + deploy + smoke test, or destroy |

---

## Roadmap

| # | Step | Talk point |
|---|---|---|
| 0 | ✅ Scaffold: MCP server, Docker, Terraform, CI | "An MCP server is just a small service" |
| 1 | ✅ **Backstage on AKS**, services reachable only via the IDP, platform read tools (`list_services`, `get_service`, `get_service_status`, `list_teams`) | The IDP is the agent's only door |
| 2 | ✅ Read tools: catalog detail and status (deploy status and logs still to do) | Rich context for the agent |
| 3 | ✅ Write tool in a separate lane: `create_service` queues a request (`trigger_deploy` still to do) | Read/write separation |
| 4 | ✅ **Human approval** through an admin endpoint outside MCP (the real scaffolder call is still a placeholder) | Human in the loop |
| 5 | **Auth** on the MCP endpoint, per-toolset tokens | Least privilege |
| 6 | **Audit log**: every tool call as structured JSON | Accountability |
| 7 | **Prompt-injection demo**: a malicious service description tries to make the agent call a write tool | Why the guardrails exist |
| 8 | Talk polish: demo script, reset script, slides | |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Browser shows `Not Found` at `localhost:8000` | Normal: the MCP server only serves `/mcp` and `/healthz`. Backstage is on port 7007. |
| `smoke-test.sh` fails at `get_service_status` right after start | Backstage is still starting (~1 min). Check `http://localhost:7007/.backstage/health/v1/readiness`. |
| `failed to create Docker client: protocol not available` | `docker_host` is set to a value for another OS (usually the Windows `npipe:` line on a Mac or Linux). Delete `infra/local/terraform.tfvars`, or set the line for your OS (see `terraform.tfvars.example`). |
| `Cannot connect to the Docker daemon` (local `terraform apply`) | Start Docker Desktop. On macOS, if `/var/run/docker.sock` doesn't exist, run `export DOCKER_HOST=$(docker context inspect --format '{{.Endpoints.docker.Host}}')` and re-run, or enable Docker Desktop → Settings → Advanced → "Allow the default Docker socket to be used". On Windows set `docker_host = "npipe:////./pipe/docker_engine"`. |
| `terraform apply` (local) fails pulling `ghcr.io/...` | Images not published or not public yet: use `image_source = "build"`. |
| `no matching manifest for linux/arm64/v8` | You pulled an image built before multi-arch support (Apple Silicon Mac). Use `image_source = "build"`, or re-run the `images` workflow and `terraform apply` again. |
| Backstage container exits / OOM | Give Docker Desktop more memory (Settings → Resources, ≥ 6 GB). |
| `deploy-azure` fails at "Check the images" | Run the `images` workflow and make both packages public (see one-time setup). |
| `deploy-azure` fails at "Azure login + find playground" | Update the three `ARM_*` secrets from the current playground page. |
| AKS create fails with a disk or policy error | Try `os_disk_type = "Managed"` in `infra/azure/variables.tf` (playground rules may change). |
| Backstage page loads but shows errors | `BACKSTAGE_BASE_URL` must match the URL in your browser; the workflow sets it, locally it's `http://localhost:7007`. |
