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

## The story (one sentence)

*An agent can look around the platform freely, but when it wants to change something, a human
decides, and that decision happens outside the agent's reach.*

## The demo

| # | You do | You say |
|---|---|---|
| 1 | Backstage > Catalog: 4 services, owners, tiers | "This is the IDP: what exists and who owns it." |
| 2 | Terminal: `curl localhost:5678` fails; `curl -H "Authorization: Bearer local-dev-token-change-me" localhost:7007/api/proxy/svc/orders-web/` answers | "The services have no door except the platform." |
| 3 | Ask: *"Which teams exist and what does each own?"* | "MCP is the API the agent uses. It called `list_teams`." |
| 4 | Ask: *"Who owns payments-api and what tier is it?"* | "`get_service`: context from the catalog, read-only." |
| 5 | Ask: *"Check whether every service is healthy."* | "`get_service_status`: the platform checks, the agent only gets healthy or not. No data, no URL of its choosing." |
| 6 | Ask: *"Create a python-service called pay-gateway for team-payments."* | "It asked for a write. Look: not created, a human must approve." |
| 7 | Terminal: `bash scripts/approve.sh list`, then `bash scripts/approve.sh approve <id>` | "Approval is an admin endpoint outside MCP. The agent has no tool and no token for it." |
| 8 | Ask: *"What happened to my request?"* | "`get_request_status`: approved." |

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
