---
title: "Incident response process"
category: runbooks
tags: [incident, process, sev]
---

# Incident response process
## Severities
- **Sev 1:** customers cannot buy, or data is exposed. All hands.
- **Sev 2:** major feature degraded. Owning team plus platform.
- **Sev 3:** minor, workaround exists.

## Steps
1. **Declare:** post in `#incidents` with the service name and severity. Page the owner from Beacon.
2. **Assign roles:** incident lead, communications lead, scribe.
3. **Find the owner and impact:** look the service up in the catalog (owner, on-call, depends on / depended on by).
4. **Mitigate first:** rollback or disable the change ([How to deploy and roll back](how-to-deploy-and-rollback)). Root cause comes later.
5. **Update** `#incidents` every 15 minutes for Sev 1.
6. **Review:** blameless post-incident review within 5 business days.
