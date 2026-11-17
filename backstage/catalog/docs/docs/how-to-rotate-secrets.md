---
title: "How to rotate secrets"
category: how-to
tags: [secrets, ledger, security]
---

# How to rotate secrets
Secrets live in **Ledger**. Rotate every 90 days, or immediately after a suspected leak.

1. Create the new value: `skyctl secret rotate <service>/<env>/<name>`.
2. Ledger keeps the old value valid for 24 hours so running pods keep working.
3. Restart the service (`skyctl restart <service>`) so it picks up the new value.
4. Verify health, then revoke the old value: `skyctl secret revoke --old`.

Never paste a secret into chat or a ticket. If you did, rotate it now and tell `#security-help`.
