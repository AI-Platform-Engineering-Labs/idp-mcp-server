"""Knowledge-base search and reading."""

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from idp_mcp import docs
from idp_mcp.server import mcp


def test_there_are_enough_articles_in_every_category():
    categories = {}
    for a in docs._articles().values():
        categories.setdefault(a["category"], []).append(a["slug"])
    assert sum(len(v) for v in categories.values()) >= 20
    assert {"onboarding", "golden-paths", "standards", "runbooks", "how-to"} <= set(categories)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("how do I roll back a deploy", "how-to-deploy-and-rollback"),
        ("payments outage", "runbook-payments-api-outage"),
        ("what is the deploy freeze", "deploy-freeze-policy"),
        ("rotate secrets ledger", "how-to-rotate-secrets"),
        ("service tier SLO availability", "service-tiers-and-slos"),
    ],
)
def test_search_finds_the_right_article_first(query, expected):
    assert docs.search(query)[0]["slug"] == expected


def test_search_filters_by_category_and_limits():
    hits = docs.search("service", category="golden-paths", limit=2)
    assert len(hits) <= 2
    assert {h["category"] for h in hits} == {"golden-paths"}


def test_empty_query_lists_articles():
    listing = docs.search("", limit=50)
    assert len(listing) >= 20 and "snippet" not in listing[0]


def test_search_with_no_match_is_empty():
    assert docs.search("zzzzqqqq") == []


def test_get_returns_the_full_article():
    article = docs.get("deploy-freeze-policy")
    assert "Friday 15:00 IST" in article["content"]
    assert article["category"] == "standards"


@pytest.mark.parametrize("slug", ["../../etc/passwd", "no-such-article", "", "A B"])
def test_get_rejects_bad_or_unknown_slugs(slug):
    with pytest.raises(ToolError):
        docs.get(slug)


@pytest.mark.asyncio
async def test_tools_work_through_the_mcp_server():
    result = await mcp.call_tool("search_docs", {"query": "on call rotation beacon"})
    text = " ".join(getattr(c, "text", "") for c in result.content)
    assert "on-call-handbook" in text
    result = await mcp.call_tool("get_doc", {"slug": "on-call-handbook"})
    assert "Beacon" in " ".join(getattr(c, "text", "") for c in result.content)
