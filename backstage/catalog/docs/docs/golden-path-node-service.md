---
title: "Golden path: Node service"
category: golden-paths
tags: [golden-path, node, web]
---

# Golden path: Node service
Template: `node-service`. Used by orders-web.

## You get
- Node 22 with TypeScript, Express, `/healthz`, structured logs.
- CI: lint, unit tests, `npm audit`, container build, SBOM.
- Static assets published to the CDN with cache headers set for you.
- Same Helm chart, dashboards and catalog registration as the Python path.

## Rules
- Do not call another team's database. Go through their API ([API design standards](api-design-standards)).
- Frontends must set the CSP headers from the template. Changes need security review.
