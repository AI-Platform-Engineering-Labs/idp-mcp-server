---
title: "Security baseline"
category: standards
tags: [security, baseline]
---

# Security baseline
Minimum for every service. The golden paths set most of this up for you.

1. Containers run as non-root, read-only filesystem, no privilege escalation.
2. Dependencies scanned in CI; critical vulnerabilities block the build.
3. Secrets come from Ledger (our vault), never from environment files in git. See [How to rotate secrets](how-to-rotate-secrets).
4. Services are private by default. Public exposure needs a security review ticket.
5. Services talk to each other through the platform, which enforces network policy.
6. Logs must not contain card numbers, passwords or full email addresses.

Report anything suspicious in `#security-help` or page the security on-call from Beacon.
