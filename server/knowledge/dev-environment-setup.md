---
title: "Developer environment setup"
category: onboarding
tags: [setup, local, docker]
---

# Developer environment setup
You need Docker Desktop, `git`, and the `skyctl` CLI (install from the internal tools page).

## Run the platform locally
1. Clone the platform repo and start the stack: `terraform apply` in `infra/local`.
2. The portal opens at http://localhost:7007 (sign in as guest locally).
3. The MCP endpoint is http://localhost:8000/mcp, so your AI assistant can use platform tools.

## Rules
- Local services publish **no ports**. They are reachable only through the portal's proxy, the same as production.
- Never copy production data to your laptop. Use the seeded fake data.
- Keep Docker images small and rebuild weekly.
