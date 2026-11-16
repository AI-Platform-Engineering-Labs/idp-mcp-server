"""The IDP the MCP server talks to.

Two backends, same functions:
  * Backstage (BACKSTAGE_URL set): services come from the Backstage catalog API, and
    service calls go through the Backstage proxy. The sample services have no public
    address, so Backstage is the only way in ("reachable via the IDP only").
  * Catalog file (no BACKSTAGE_URL): server/catalog/services.yaml. Used by unit tests
    and for running the MCP server on its own.

The MCP server authenticates to Backstage with a static token (BACKSTAGE_TOKEN) that
Backstage only accepts for the catalog and proxy plugins: least privilege.
"""

import os
import re

import httpx
from mcp.server.mcpserver.exceptions import ToolError

from idp_mcp.catalog import load_services

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
TIMEOUT = httpx.Timeout(10.0)


class PlatformError(ToolError):
    """A problem talking to the platform. As a ToolError its message is shown to the
    agent (other exceptions are hidden from it and logged as crashes)."""


def backstage_url() -> str | None:
    url = os.environ.get("BACKSTAGE_URL", "").rstrip("/")
    return url or None


def _headers() -> dict[str, str]:
    token = os.environ.get("BACKSTAGE_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _from_entity(e: dict) -> dict:
    meta, spec = e.get("metadata", {}), e.get("spec", {})
    return {
        "name": meta.get("name"),
        "description": meta.get("description", ""),
        "owner": str(spec.get("owner", "")).removeprefix("group:"),
        "system": spec.get("system", ""),
        "lifecycle": spec.get("lifecycle", ""),
        "type": spec.get("type", ""),
        "tier": meta.get("annotations", {}).get("idp.demo/tier", ""),
    }


def list_services() -> list[dict]:
    base = backstage_url()
    if not base:
        return load_services()
    try:
        r = httpx.get(
            f"{base}/api/catalog/entities/by-query",
            params={"filter": "kind=component", "limit": 100},
            headers=_headers(),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise PlatformError(f"Backstage catalog is not reachable: {exc}") from exc
    return [_from_entity(e) for e in r.json().get("items", [])]


def call_service(name: str, path: str = "/") -> dict:
    """GET a service through the Backstage proxy (/api/proxy/svc/<name>)."""
    if not NAME_RE.match(name):
        raise PlatformError("Invalid service name.")
    known = {s["name"] for s in list_services()}
    if name not in known:
        raise PlatformError(f"Unknown service '{name}'. Known services: {sorted(known)}")
    if not path.startswith("/") or ".." in path or "//" in path:
        raise PlatformError("Path must start with '/' and must not contain '..' or '//'.")

    base = backstage_url()
    if not base:
        raise PlatformError("No platform configured (BACKSTAGE_URL is not set).")
    try:
        r = httpx.get(f"{base}/api/proxy/svc/{name}{path}", headers=_headers(), timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise PlatformError(f"Could not reach {name} through Backstage: {exc}") from exc
    return {"service": name, "path": path, "status": r.status_code, "body": r.text[:2000]}
