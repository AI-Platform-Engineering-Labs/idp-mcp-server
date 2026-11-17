---
title: "Runbook: orders-web slow or erroring"
category: runbooks
tags: [runbook, orders-web, latency]
---

# Runbook: orders-web slow or erroring
Owner: team-storefront. Tier: standard. Depends on: payments-api, customers-api.

1. Check status of orders-web, payments-api and customers-api. Slow checkout is usually a dependency.
2. If a dependency is down, follow its runbook and tell team-storefront; do not restart orders-web needlessly.
3. If dependencies are healthy, check the CDN cache hit rate; a drop below 80% means a bad release. Roll back.
4. Confirm recovery: p95 page load under 1.5 seconds for 10 minutes.
