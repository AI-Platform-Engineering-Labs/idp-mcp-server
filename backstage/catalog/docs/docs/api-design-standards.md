---
title: "API design standards"
category: standards
tags: [api, standards, rest]
---

# API design standards
- REST over HTTPS, JSON bodies, `snake_case` fields, ISO 8601 UTC timestamps.
- Version in the path: `/v1/...`. Breaking changes need a new major version and a 90-day overlap.
- Errors use `{ "error": { "code", "message", "request_id" } }`.
- Pagination: cursor based, `limit` max 100.
- Every API is registered in the catalog as an API entity with an OpenAPI file.
- Idempotency: all `POST` requests that create money movement require an `Idempotency-Key` header (payments-api enforces this).
- Authentication: service to service uses short-lived tokens from the platform; never long-lived keys in code.
