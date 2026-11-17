---
title: "Service tiers and SLOs"
category: standards
tags: [tier, slo, reliability]
---

# Service tiers and SLOs
Every service has a tier in the catalog (`critical`, `standard`, `experimental`).

| Tier | Availability SLO | Response to page | Examples |
|---|---|---|---|
| critical | 99.95% | 15 minutes, 24/7 | payments-api, customers-api |
| standard | 99.5% | 30 minutes, working hours + best effort overnight | orders-web, notifications-worker |
| experimental | none | next business day | prototypes |

- Critical services need two on-call engineers and a tested rollback.
- Tier changes need a pull request to the catalog and approval from the service owner and `team-platform`.
- Error budget policy: if a service burns 100% of its monthly budget, feature work pauses until the budget recovers.
