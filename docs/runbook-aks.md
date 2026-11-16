# Runbook: AKS + Backstage IDP + MCP server in the KodeKloud Azure playground

Use this when you want a working demo cluster: **AKS** running the **Backstage IDP**, the **MCP
server** and three sample services, so Copilot or Claude can use the platform through MCP.

Everything is done from GitHub Actions. You need no Azure CLI, Terraform or kubectl on your laptop.

- **Time:** about 5 minutes of your work, about 15 minutes for the workflow.
- **Who:** the person giving the demo (repo admin).
- **When:** each time you start a new playground session.

---

## 1. What you will end up with

```
GitHub Actions ──(service principal)──▶ Azure playground subscription
                                           └─ resource group  kml_rg_main_…   (pre-created, only read)
                                                ├─ storage account  tfidp…    Terraform state
                                                └─ AKS  idp-aks-<suffix>  (2 × Standard_D2s_v3)
                                                     └─ namespace idp
                                                          ├─ backstage        (public IP)  the IDP portal
                                                          ├─ mcp-server       (public IP)  /mcp for Copilot / Claude
                                                          └─ payments-api, orders-web, notifications-worker
                                                                (private; only Backstage can reach them)
```

You end with two URLs in the run summary: the **Backstage portal** and the **MCP endpoint**.

---

## 2. The values you need, and where each comes from

### 2.1 From the KodeKloud playground (change with every new playground)

Start the playground at *kodekloud.com → Cloud Playgrounds → Azure*. The start page shows the
credentials of a **service principal** (a robot account for Azure) and the playground's resource
group. Label names can differ slightly; the Azure portal also shows these under **Microsoft Entra ID**.

| Value | What it looks like | GitHub setting to create | Required |
|---|---|---|---|
| **Application (client) ID** | GUID, `xxxxxxxx-xxxx-…` | Repository **secret** `ARM_CLIENT_ID` | yes |
| **Client secret** | long random string | Repository **secret** `ARM_CLIENT_SECRET` | yes |
| **Tenant (directory) ID** | GUID | Repository **secret** `ARM_TENANT_ID` | yes |
| **Subscription ID** | GUID | Repository **secret** `ARM_SUBSCRIPTION_ID` | no, found automatically |
| **Resource group name** | `kml_rg_main_…` | Repository **variable** `RESOURCE_GROUP` | no, found automatically |

How to set them: repo **Settings → Secrets and variables → Actions**. Secrets are on the *Secrets*
tab, the resource group on the *Variables* tab. Or from Git Bash:

```bash
export ARM_CLIENT_ID=...  ARM_CLIENT_SECRET=...  ARM_TENANT_ID=...
bash scripts/set-sandbox-secrets.sh
```

**If your subscription and resource group really are the same every time**, set
`ARM_SUBSCRIPTION_ID` and `RESOURCE_GROUP` once and leave them. That's the most explicit setup:
the workflow uses exactly those. If they are *not* the same each time, leave both unset: the
workflow finds them by itself. (A `RESOURCE_GROUP` left over from an old playground is ignored with
a warning.) Only the client ID and client secret normally change per session, and the tenant may too.

The secret value is shown once on the playground page. Copy it straight into GitHub. Never paste
it into chat, an issue or a commit.

### 2.2 One-time GitHub setup (never changes)

| Item | Where | Why |
|---|---|---|
| Images published | Actions → **images** → Run workflow (it also runs on every merge to `main`) | The cluster pulls `ghcr.io/ai-platform-engineering-labs/idp-backstage` and `idp-mcp-server` |
| Both packages **Public** | Org → Packages → each package → Package settings → Change visibility. If *Public* is greyed out: org **Settings → Packages → Package creation → Public** first | AKS pulls anonymously: the playground has no way to give it registry credentials |
| Environment `sandbox` with you as **Required reviewer** | Repo Settings → Environments | A human approves before anything is created or destroyed (the same human-in-the-loop idea as the talk) |
| Workflow permissions | Settings → Actions → General: allow GitHub Actions to run | needed for `images` to publish packages |

---

## 3. Procedure

### Step 1: Start the playground and set the three secrets (section 2.1)

### Step 2: Run the preflight (read-only, 1 minute)

**Actions → deploy-azure → Run workflow → `action: preflight`** (the default).

It logs in with your secrets and checks, changing nothing:

| Check | Meaning if it fails |
|---|---|
| Login works, subscription and resource group found | Secrets are wrong or the playground has expired → redo section 2.1 |
| `Standard_D2s_v3` available in the group's region | The playground's one allowed AKS node size is unavailable there |
| No leftover AKS cluster / existing state storage | A warning that an earlier run is still there |
| Both images public and built for `linux/amd64` | Run `images`, make the packages public |

The result is in the run's **Summary** with ✅ / ⚠️ / ❌ lines. Fix every ❌ before continuing.

### Step 3: Apply (about 15 minutes)

**Run workflow → `action: apply`**, keep `image_tag: latest`. Approve the `sandbox` environment when
it asks. The jobs and what they do:

| Job / step | What happens | If it fails, look at |
|---|---|---|
| `infra` → Azure login + find playground | Logs in, finds subscription and resource group | the 3 secrets |
| `infra` → Terraform state storage | Creates a storage account for Terraform state if missing | login / permissions |
| `infra` → terraform plan | Shows what will be created (in the Summary) | the plan text |
| `infra` → terraform apply | Creates the AKS cluster (about 6-8 minutes) | policy errors: see section 6 |
| `k8s` → Get cluster credentials, Shared token | Creates namespace `idp` and a random token Backstage and the MCP server share, kept as a Kubernetes secret | |
| `k8s` → Apply manifests | Deploys Backstage, the MCP server and the 3 services from `k8s/` | |
| `k8s` → Wait for public IPs, Tell Backstage its URL | Waits for the two load balancers and sets Backstage's address | |
| `k8s` → Smoke test through the MCP server | Calls `list_services` and `call_service` like an agent would | |
| `k8s` → Show that services are reachable only via the IDP | Proves a direct call to `payments-api` is blocked | a warning here means the network policy isn't enforced |

### Step 4: Verify

The run **Summary** shows the two URLs. Check them in this order:

1. **Backstage:** open `http://<backstage-ip>`, click *Enter* (guest). **Catalog** lists `payments-api`,
   `orders-web`, `notifications-worker` and `idp-mcp-server`.
2. **MCP server health:** `http://<mcp-ip>/healthz` shows `{"status":"ok",…}`.
3. **MCP tools from your laptop**: `bash scripts/smoke-test.sh http://<mcp-ip>` ends with
   *OK: payments-api answered through Backstage*.
4. **Copilot / Claude:**
   - VS Code: *MCP: List Servers* → `idp-aks` → paste `http://<mcp-ip>/mcp` → Start. In Copilot Chat (Agent mode) ask
     *"List the services owned by team-payments"* and *"Check that every service in the shop system is healthy."*
   - Claude Code: `claude mcp add --transport http idp http://<mcp-ip>/mcp`.
5. Optional, to look inside the cluster: in the Azure portal open the **Cloud Shell** (or any machine with
   Azure CLI) and run `az aks get-credentials -g <rg> -n <cluster>` then `kubectl -n idp get pods,svc`.

### Step 5: Tear down (when done)

**Run workflow → `action: destroy`** removes the cluster. The playground deletes everything when
the session expires anyway, so this is only for finishing early. Afterwards you can remove the stale
secrets: `bash scripts/sandbox-down.sh`.

---

## 4. The demo, step by step (what to say and show)

| # | Do | Point to make |
|---|---|---|
| 1 | Show Backstage's catalog | "This is the IDP: what exists and who owns it." |
| 2 | Show `kubectl get svc` or the architecture diagram: the 3 services have no public IP | "The services can't be reached except through the platform." |
| 3 | In Copilot: *"Which services does team-payments own?"* | The agent calls the MCP tool `list_services`, which asks Backstage. |
| 4 | *"Is payments-api healthy?"* | `call_service` goes MCP → Backstage proxy → service. |
| 5 | Try to reach a service directly from your laptop (it fails) | Only the IDP is a door, and the agent uses the same door as a human. |
| 6 | Show the MCP token's limits (`docs/architecture.md`, "Guardrails") | The agent has a narrow token, not cluster access. |

---

## 5. How this compares with a real setup

This demo is realistic in shape but simplified where the playground or the time limit require it.
Say this honestly in the talk, it's a strength:

| Area | In this demo | In a real company |
|---|---|---|
| Azure login from CI | Service principal + client secret in GitHub secrets (the playground blocks OIDC) | **OIDC federated credentials**, no stored secret |
| Approval | `sandbox` environment with a required reviewer | Same, plus branch protection and a separate prod subscription |
| Terraform state | Storage account in the same resource group, key access | Dedicated state account, private endpoint, Entra ID access |
| Images | Public GHCR packages | Private ACR attached to AKS with a managed identity, signed images |
| Backstage sign-in | Guest, anyone with the URL | SSO (Entra ID / GitHub), permission policy |
| Backstage database | In-memory, reloaded from files | PostgreSQL, catalog from Git repos |
| Exposure | Public load balancers over HTTP | Private ingress with TLS and a WAF, MCP endpoint behind authentication |
| Agent access | One static token for catalog + proxy only | Per-user tokens, per-tool scopes, audit log (roadmap steps 4-6) |
| Cluster | 2 nodes, Free tier, no monitoring (playground rule) | Multiple node pools across zones, monitoring and alerts |

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Run stops at "Azure login": *secret is empty* | A secret name is missing or misspelled | Section 2.1: exact names `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID` |
| "Azure login failed" | Playground expired, or secrets from an older playground | Start a new playground, update all three secrets |
| "Could not find the playground resource group" | The service principal sees no group named `kml_rg_main_…` | Set variable `RESOURCE_GROUP` to the exact name from the playground page |
| Preflight ❌ "can't be pulled anonymously" | `images` workflow not run, or packages private | Run `images`; make both packages Public (section 2.2) |
| Preflight ❌ "no linux/amd64" | Old image published before the multi-arch change | Re-run `images` |
| `terraform apply` fails: *RequestDisallowedByPolicy* or a VM size / SKU error | The playground allows only `Standard_D2s_v3`, max 2 nodes, 1 pool | Leave `node_vm_size` and `node_count` at the defaults |
| `terraform apply` fails mentioning the OS disk | Ephemeral OS disk refused | In `infra/azure/variables.tf` set `os_disk_type` default to `"Managed"` |
| `terraform apply` fails: *quota* / *cores* | Another cluster or VMs already use the playground's core limit | Run `action: destroy`, or delete the old resources in the portal |
| "No public IP for backstage after 5 minutes" | The playground allows only 3 load balancers per session | Check for leftover load balancers; destroy and re-run |
| Backstage pod `Pending` | Not enough memory on the nodes | `kubectl -n idp describe pod`; make sure both nodes are up (`node_count = 2`) |
| Backstage opens but shows errors / blank page | `BACKSTAGE_BASE_URL` doesn't match the URL in your browser | The workflow sets it; re-run `apply`, and open the exact URL from the summary |
| Smoke test: `call_service` fails | Backstage still starting, or the token doesn't match | Wait a minute and re-run `scripts/smoke-test.sh`; re-run `apply` |
| Warning "payments-api answered a direct call" | Network policy isn't enforced | Check the cluster uses the Cilium network policy (`infra/azure/main.tf`) |
| Same secret works yesterday, fails today | Playground sessions are short-lived | Start a new one and update the secrets |

---

## 7. Checklist (print this)

- [ ] Playground started, page open
- [ ] `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID` updated in GitHub
- [ ] (once) packages `idp-backstage` and `idp-mcp-server` are **Public**
- [ ] (once) environment `sandbox` has a required reviewer
- [ ] deploy-azure → **preflight** → all ✅
- [ ] deploy-azure → **apply** → approve → green
- [ ] Backstage URL opens, catalog lists the services
- [ ] `smoke-test.sh` says OK
- [ ] Copilot / Claude connected to `http://<mcp-ip>/mcp`
- [ ] After the session: `destroy` (optional) and `sandbox-down.sh`
