---
title: "How to deploy and roll back"
category: how-to
tags: [deploy, rollback, release]
---

# How to deploy and roll back
## Deploy
1. Merge to `main`; CI builds and deploys to staging automatically.
2. Check staging health and run the smoke test.
3. Promote to production with `skyctl promote <service>` (needs the `deployer` role).
4. Watch the dashboard for 15 minutes.

## Roll back
`skyctl rollback <service>` returns to the previous version in under 2 minutes. Roll back first, investigate after.

## Rules
- No deploys during the [deploy freeze](deploy-freeze-policy).
- Critical services deploy one at a time and never in the last hour of the working day.
