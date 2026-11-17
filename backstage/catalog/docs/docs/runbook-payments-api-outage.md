---
title: "Runbook: payments-api outage"
category: runbooks
tags: [runbook, payments-api, critical]
---

# Runbook: payments-api outage
Owner: team-payments. Tier: critical. Dependency: customers-api.

## Symptoms
Checkout fails, `get status` shows payments-api unhealthy, orders-web error rate rises.

## Impact
orders-web and notifications-worker are affected (orders cannot be paid, confirmation emails stop).

## Steps
1. Declare a Sev 1 ([Incident response](incident-response-process)) and page team-payments on-call.
2. Check whether the last deploy was in the past hour; if yes, roll back ([How to deploy and roll back](how-to-deploy-and-rollback)).
3. Check customers-api health: if it is down, fix that first (payments-api depends on it).
4. If the dependency is healthy and rollback does not help, scale payments-api to 6 replicas and open the dashboard linked in the catalog.
5. Tell `#incidents` when payments recover; confirm orders-web checkout works.
