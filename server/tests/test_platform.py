"""Tests for the Backstage backend, with Backstage faked by monkeypatching httpx.get."""

import httpx
import pytest

from idp_mcp import platform

COMPONENTS = {
    "items": [
        {
            "kind": "Component",
            "metadata": {
                "name": "payments-api",
                "description": "Payments",
                "tags": ["python"],
                "annotations": {"idp.demo/tier": "critical"},
            },
            "spec": {"owner": "group:team-payments", "system": "shop", "lifecycle": "production"},
            "relations": [
                {"type": "dependsOn", "targetRef": "component:default/customers-api"},
                {"type": "dependsOn", "targetRef": "resource:default/payments-db"},
                {"type": "dependencyOf", "targetRef": "component:default/orders-web"},
                {"type": "ownedBy", "targetRef": "group:default/team-payments"},
            ],
        },
        {
            "kind": "Component",
            "metadata": {"name": "orders-web"},
            "spec": {"owner": "team-storefront", "system": "shop"},
        },
    ]
}
TEMPLATES = {
    "items": [
        {
            "metadata": {"name": "python-service", "title": "Python service"},
            "spec": {"type": "service"},
        },
        {"metadata": {"name": "node-service"}, "spec": {"type": "website"}},
    ]
}
GROUPS = {
    "items": [{"metadata": {"name": "team-payments"}}, {"metadata": {"name": "team-storefront"}}]
}


@pytest.fixture
def fake_backstage(monkeypatch):
    class Calls(list):
        state = {"proxy_status": 200}

    calls = Calls()
    state = calls.state

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append({"url": url, "params": params, "headers": headers})
        req = httpx.Request("GET", url)
        if url.endswith("/api/catalog/entities/by-query"):
            kind = (params or {}).get("filter")
            body = {"kind=group": GROUPS, "kind=template": TEMPLATES}.get(kind, COMPONENTS)
            return httpx.Response(200, json=body, request=req)
        if "/api/catalog/entities/by-name/component/default/payments-api" in url:
            return httpx.Response(200, json=COMPONENTS["items"][0], request=req)
        if "/api/proxy/svc/orders-web/" in url:
            return httpx.Response(state["proxy_status"], text="SECRET BODY", request=req)
        return httpx.Response(404, request=req)

    monkeypatch.setenv("BACKSTAGE_URL", "http://backstage:7007/")
    monkeypatch.setenv("BACKSTAGE_TOKEN", "t0ken")
    monkeypatch.setattr(platform.httpx, "get", fake_get)
    return calls


def test_list_services_from_backstage(fake_backstage):
    services = platform.list_services()
    assert [s["name"] for s in services] == ["payments-api", "orders-web"]
    assert services[0]["owner"] == "team-payments"  # "group:" prefix removed
    assert fake_backstage[0]["headers"] == {"Authorization": "Bearer t0ken"}


def test_get_service_has_detail(fake_backstage):
    detail = platform.get_service("payments-api")
    assert detail["tier"] == "critical"
    assert detail["tags"] == ["python"]
    assert detail["depends_on"] == ["customers-api", "resource:payments-db"]
    assert detail["depended_on_by"] == ["orders-web"]  # what breaks if payments-api is down
    assert "resource:payments-db" in detail["depends_on"]


def test_get_service_unknown_or_invalid(fake_backstage):
    with pytest.raises(platform.PlatformError):
        platform.get_service("nope")
    with pytest.raises(platform.PlatformError):
        platform.get_service("../admin")


def test_status_reports_only_health_not_the_body(fake_backstage):
    result = platform.get_service_status("orders-web")
    assert result == {"service": "orders-web", "healthy": True, "http_status": 200}
    assert "SECRET" not in str(result)
    assert fake_backstage[-1]["url"] == "http://backstage:7007/api/proxy/svc/orders-web/"


def test_status_unhealthy(fake_backstage):
    fake_backstage.state["proxy_status"] = 503
    assert platform.get_service_status("orders-web")["healthy"] is False


def test_status_unknown_service_is_refused(fake_backstage):
    with pytest.raises(platform.PlatformError):
        platform.get_service_status("not-in-catalog")


def test_list_templates_from_backstage(fake_backstage):
    templates = platform.list_templates()
    assert [t["name"] for t in templates] == ["python-service", "node-service"]
    assert templates[0]["title"] == "Python service"


def test_list_teams_with_their_services(fake_backstage):
    teams = platform.list_teams()
    assert teams == [
        {"team": "team-payments", "services": ["payments-api"]},
        {"team": "team-storefront", "services": ["orders-web"]},
    ]


@pytest.mark.parametrize(
    ("template", "name", "owner", "message"),
    [
        ("rust-service", "new-svc", "team-payments", "Unknown template"),
        ("python-service", "Bad Name!", "team-payments", "Service name"),
        ("python-service", "orders-web", "team-payments", "already exists"),
        ("python-service", "new-svc", "team-nobody", "Unknown team"),
    ],
)
def test_validate_new_service_rejects_bad_requests(fake_backstage, template, name, owner, message):
    with pytest.raises(platform.PlatformError, match=message):
        platform.validate_new_service(template, name, owner)


def test_validate_new_service_accepts_a_good_request(fake_backstage):
    platform.validate_new_service("python-service", "new-svc", "team-payments")


def test_file_catalog_fallback_without_backstage():
    assert {s["name"] for s in platform.list_services()} >= {"payments-api", "orders-web"}
    assert {
        "team": "team-payments",
        "services": ["customers-api", "payments-api"],
    } in platform.list_teams()
    with pytest.raises(platform.PlatformError, match="BACKSTAGE_URL"):
        platform.get_service_status("orders-web")
    detail = platform.get_service("customers-api")
    assert detail["depended_on_by"] == ["orders-web", "payments-api"]
    assert detail["oncall"].endswith("@example.com")
