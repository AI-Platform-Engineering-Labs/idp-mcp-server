---
title: "Golden path: Python service"
category: golden-paths
tags: [golden-path, python, api]
---

# Golden path: Python service
Template: `python-service`. Used by payments-api.

## You get
- FastAPI skeleton with `/healthz` and `/readyz`, structured JSON logs, OpenTelemetry traces.
- CI: ruff, pytest (coverage gate 85%), dependency audit, container build, SBOM.
- Helm chart `skyline-service` with tier-based defaults (see [Service tiers and SLOs](service-tiers-and-slos)).
- Dashboards and alerts created for your tier.
- Catalog entry with owner, tier and on-call.

## Rules
- Python 3.12, dependencies pinned, no `latest` tags.
- Health endpoint must answer in under 200 ms; the platform uses it for status checks.
