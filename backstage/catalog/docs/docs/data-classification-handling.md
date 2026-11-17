---
title: "Data classification and handling"
category: standards
tags: [data, pii, privacy]
---

# Data classification and handling
| Class | Example | Rules |
|---|---|---|
| Public | product names | none |
| Internal | service metrics | company accounts only |
| Confidential | order history | encrypted at rest, access logged |
| Restricted | card data, customer contact details | only the owning team; no copies outside prod; masked in logs |

- **customers-api** stores Restricted data (profiles and contact details). Only team-payments may access it.
- **payments-api** handles card tokens. We never store full card numbers.
- Analytics gets aggregated or pseudonymised data only.
- A suspected data leak is a **severity 1 incident** immediately ([Incident response](incident-response-process)).
