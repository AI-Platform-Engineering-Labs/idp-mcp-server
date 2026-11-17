"""The IDP the MCP server talks to.

Read functions (list_services, get_service, get_service_status, list_teams) and the
validation for the create_service write action live here. Two backends, same functions:
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
        "oncall": meta.get("annotations", {}).get("idp.demo/oncall", ""),
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


def _require_service(name: str) -> dict:
    if not NAME_RE.match(name):
        raise PlatformError("Invalid service name.")
    services = {s["name"]: s for s in list_services()}
    if name not in services:
        raise PlatformError(f"Unknown service '{name}'. Known services: {sorted(services)}")
    return services[name]


def get_service(name: str) -> dict:
    """One service from the catalog, with a bit more detail than list_services."""
    summary = _require_service(name)
    base = backstage_url()
    if not base:
        depends_on = summary.get("depends_on", [])
        used_by = sorted(s["name"] for s in list_services() if name in s.get("depends_on", []))
        return {**summary, "depends_on": depends_on, "depended_on_by": used_by}
    try:
        r = httpx.get(
            f"{base}/api/catalog/entities/by-name/component/default/{name}",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise PlatformError(f"Backstage catalog is not reachable: {exc}") from exc
    entity = r.json()
    detail = _from_entity(entity)
    detail["tags"] = entity.get("metadata", {}).get("tags", [])
    detail["links"] = entity.get("metadata", {}).get("links", [])
    relations = entity.get("relations", [])

    def related(kind: str) -> list[str]:
        # components by plain name, other kinds as "resource:name" / "api:name"
        out = []
        for r in relations:
            if r.get("type") != kind:
                continue
            ref_kind, _, rest = r.get("targetRef", "").partition(":")
            name = rest.rsplit("/", 1)[-1]
            out.append(name if ref_kind == "component" else f"{ref_kind}:{name}")
        return sorted(out)

    # What this service needs, and what breaks if it goes down.
    detail["depends_on"] = related("dependsOn")
    detail["depended_on_by"] = related("dependencyOf")
    return detail


def get_service_status(name: str) -> dict:
    """Is the service up? The platform asks it through the Backstage proxy and reports only
    healthy/unhealthy and the HTTP status: no body, no caller-chosen path."""
    _require_service(name)
    base = backstage_url()
    if not base:
        raise PlatformError("No platform configured (BACKSTAGE_URL is not set).")
    try:
        r = httpx.get(f"{base}/api/proxy/svc/{name}/", headers=_headers(), timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        return {"service": name, "healthy": False, "http_status": None, "error": str(exc)}
    return {"service": name, "healthy": r.status_code < 400, "http_status": r.status_code}


def list_teams() -> list[dict]:
    """Teams (Backstage groups) and the services each one owns."""
    services = list_services()
    base = backstage_url()
    if base:
        try:
            r = httpx.get(
                f"{base}/api/catalog/entities/by-query",
                params={"filter": "kind=group", "limit": 100},
                headers=_headers(),
                timeout=TIMEOUT,
            )
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise PlatformError(f"Backstage catalog is not reachable: {exc}") from exc
        names = [e["metadata"]["name"] for e in r.json().get("items", [])]
    else:
        names = sorted({s["owner"] for s in services if s.get("owner")})
    return [
        {"team": t, "services": sorted(s["name"] for s in services if s.get("owner") == t)}
        for t in sorted(names)
    ]


# Fallback golden paths when there is no Backstage (unit tests, stdio without a platform).
FALLBACK_TEMPLATES = (
    {
        "name": "python-service",
        "title": "Python service",
        "description": "FastAPI service",
        "type": "service",
    },
    {
        "name": "node-service",
        "title": "Node service",
        "description": "Node.js web service",
        "type": "service",
    },
)


def list_templates() -> list[dict]:
    """Software templates (Backstage Template entities): the golden paths."""
    base = backstage_url()
    if not base:
        return [dict(t) for t in FALLBACK_TEMPLATES]
    try:
        r = httpx.get(
            f"{base}/api/catalog/entities/by-query",
            params={"filter": "kind=template", "limit": 100},
            headers=_headers(),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise PlatformError(f"Backstage catalog is not reachable: {exc}") from exc
    return [
        {
            "name": e["metadata"]["name"],
            "title": e["metadata"].get("title", e["metadata"]["name"]),
            "description": e["metadata"].get("description", ""),
            "type": e.get("spec", {}).get("type", ""),
        }
        for e in r.json().get("items", [])
    ]


def validate_new_service(template: str, name: str, owner: str) -> None:
    """Check a create_service request before it is queued for human approval."""
    templates = [t["name"] for t in list_templates()]
    if template not in templates:
        raise PlatformError(f"Unknown template '{template}'. Allowed templates: {templates}")
    if not NAME_RE.match(name):
        raise PlatformError("Service name must be lowercase letters, digits and '-' (max 63).")
    if name in {s["name"] for s in list_services()}:
        raise PlatformError(f"A service called '{name}' already exists.")
    teams = [t["team"] for t in list_teams()]
    if owner not in teams:
        raise PlatformError(f"Unknown team '{owner}'. Known teams: {teams}")
