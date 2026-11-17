---
title: "Naming conventions"
category: standards
tags: [naming, standards]
---

# Naming conventions
- **Services:** lowercase, hyphenated, noun-based: `payments-api`, `orders-web`. Suffix with the kind: `-api`, `-web`, `-worker`.
- **Teams:** `team-<name>`.
- **Environments:** `dev`, `staging`, `prod`. Never `test` or `qa`.
- **Secrets:** `<service>/<env>/<name>`, e.g. `payments-api/prod/db-password`.
- **Branches:** `feature/<ticket>-short-name`, `fix/<ticket>-short-name`.
- **Metrics:** `skyline_<service>_<thing>_<unit>`.

Names are validated when you request a service. Invalid names are rejected before anything is created.
