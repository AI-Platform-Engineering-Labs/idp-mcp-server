---
title: "Access and accounts"
category: onboarding
tags: [access, sso, onboarding]
---

# Access and accounts
All access goes through SSO groups. Nobody gets shared accounts.

## Standard access (everyone)
Source control, the portal, the chat workspace, the staging cluster (read/write to your team namespace).

## Requesting more
Use `skyctl access request --team <team> --role <role>`. Roles: `developer` (default), `deployer` (can promote to production), `viewer`.
- `deployer` needs 3 months at Skyline and your manager's approval.
- Production data access is **never** granted for convenience. See [Data classification](data-classification-handling).

## Offboarding
Access is removed within 1 hour of the last working day by the platform team. Teams must hand over service ownership in the catalog first.
