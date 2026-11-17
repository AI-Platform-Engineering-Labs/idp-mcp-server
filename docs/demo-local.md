# Talk cheat sheet: the local demo

One page to run on stage. Everything runs on the laptop; no Azure needed.

## Before the talk (once, then rehearse)

```bash
cd infra/local
terraform destroy                      # if an old stack is running
docker rmi ghcr.io/ai-platform-engineering-labs/idp-mcp-server:latest \
           ghcr.io/ai-platform-engineering-labs/idp-backstage:latest   # forget stale images
terraform apply                        # yes
cd ../..
ADMIN_TOKEN=local-admin-token bash scripts/smoke-test.sh   # every line OK
```

Connect the client once:

- **VS Code:** open the `idp-mcp-server` folder, Cmd+Shift+P, *MCP: List Servers*, `idp-local-http`, Start.
- **Claude Code:** `claude mcp add --transport http idp http://localhost:8000/mcp`

Open these windows: Backstage http://localhost:7007 (Enter as guest), the AI client, a terminal.

## The story

*It is a bad day: checkout is failing. An engineer asks the agent for help. The agent can look
around the platform freely, work out what is broken and who to call, but when it wants to
change something, a human decides, outside the agent's reach.*

## Act 1: an incident (about 4 minutes)

| # | You do | You say |
|---|---|---|
| 1 | Backstage > Catalog: 4 services with owners, tiers, dependencies | "This is the IDP: what exists, who owns it, what depends on what." |
| 2 | Terminal: `curl localhost:5678` fails; `curl -H "Authorization: Bearer local-dev-token-change-me" localhost:7007/api/proxy/svc/orders-web/` answers | "The services have no door except the platform." |
| 3 | Break something live: `docker stop payments-api` | "Payments just went down. Checkout is failing." |
| 4 | Ask: *"Checkout is failing. Check the health of every service, find what is down, tell me who owns it, who is on call, and which other services are affected."* | "The agent uses MCP tools: `list_services`, `get_service_status`, `get_service`. No dashboards, no tickets." |
| 5 | Show the answer: payments-api is down, team-payments owns it, the on-call contact, and orders-web (and notifications-worker through it) are affected | "Ownership, on-call and dependencies came from the catalog. That is the value of an IDP, now reachable by an agent." |
| 6 | Terminal: `docker start payments-api`, then ask *"Is everything healthy again?"* | "Fixed. The agent only looked. It could not touch anything." |

## Act 2: the guardrail (about 3 minutes)

| # | You do | You say |
|---|---|---|
| 7 | Ask: *"Create a python-service called pay-gateway for team-payments."* | "Now it wants to change something. Look: not created, a human must approve." |
| 8 | Terminal: `bash scripts/approve.sh list`, then `bash scripts/approve.sh approve <id>` | "Approval is an admin endpoint outside MCP. The agent has no tool and no token for it." |
| 9 | Ask: *"What happened to my request?"* | "`get_request_status`: approved." |

Honest note if asked: the approval flow is real; the "create" step behind it is a placeholder
(nothing is scaffolded), and the request store is in memory.

## If something goes wrong

| Symptom | Fix |
|---|---|
| Tools not listed | MCP: List Servers > `idp-local-http` > Restart; Claude Code: `/mcp` > reconnect |
| Old tool list (`call_service` appears) | Old image: redo the `docker rmi` + `terraform apply` above |
| `get_service_status` says not healthy right after start | Wait a minute for Backstage, ask again |
| Approve says unauthorized | Use the default token (`local-admin-token`) or export `ADMIN_TOKEN` |
| Anything else | `terraform destroy` then `terraform apply`; screenshots of each step as a backup |
