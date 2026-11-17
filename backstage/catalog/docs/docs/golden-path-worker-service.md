---
title: "Golden path: Worker service"
category: golden-paths
tags: [golden-path, worker, queue]
---

# Golden path: Worker service
For queue consumers and scheduled jobs. Used by notifications-worker.

## You get
- Go skeleton with graceful shutdown, retry with backoff, dead-letter queue wiring.
- A `/healthz` endpoint (workers still need one) and a heartbeat metric.
- Alert when the queue age exceeds 5 minutes (tier `standard`) or 1 minute (tier `critical`).

## Rules
- Handlers must be idempotent: messages can arrive twice.
- Max processing time per message: 30 seconds. Longer work belongs in a job.
