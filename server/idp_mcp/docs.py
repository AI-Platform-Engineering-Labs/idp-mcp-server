"""The platform's knowledge base: how-tos, golden paths, standards and runbooks.

The articles are Markdown files in server/knowledge (title, category and tags in the front
matter). In a real IDP this is TechDocs or a wiki; here it is plain files so the demo has
company-internal knowledge that is not on the internet. Search is simple keyword scoring: no
embeddings, no extra service, easy to explain.
"""

import os
import re
from functools import lru_cache
from pathlib import Path

import yaml
from mcp.server.mcpserver.exceptions import ToolError

DEFAULT_DOCS = Path(__file__).resolve().parent.parent / "knowledge"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
WORD_RE = re.compile(r"[a-z0-9]+")
MAX_CHARS = 20000
STOP = {
    "the",
    "a",
    "an",
    "to",
    "of",
    "and",
    "or",
    "in",
    "on",
    "for",
    "is",
    "do",
    "i",
    "how",
    "what",
}


class DocsError(ToolError):
    """Shown to the agent (a ToolError), e.g. for an unknown article."""


def docs_path() -> Path:
    return Path(os.environ.get("DOCS_PATH", DEFAULT_DOCS))


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, dict]:
    articles = {}
    for f in sorted(Path(path).glob("*.md")):
        text = f.read_text(encoding="utf-8")
        meta, body = {}, text
        if text.startswith("---\n"):
            _, front, body = text.split("---\n", 2)
            meta = yaml.safe_load(front) or {}
        articles[f.stem] = {
            "slug": f.stem,
            "title": meta.get("title", f.stem),
            "category": meta.get("category", ""),
            "tags": meta.get("tags", []),
            "body": body.strip(),
        }
    return articles


def _articles() -> dict[str, dict]:
    return _load(str(docs_path()))


def _words(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower()) if w not in STOP]


def _snippet(body: str, words: list[str]) -> str:
    flat = " ".join(body.split())
    lower = flat.lower()
    hits = [lower.find(w) for w in words if lower.find(w) >= 0]
    start = max(min(hits) - 60, 0) if hits else 0
    return ("..." if start else "") + flat[start : start + 240] + "..."


def search(query: str = "", category: str | None = None, limit: int = 5) -> list[dict]:
    """Best matching articles. An empty query lists them all (newest categories first)."""
    items = [a for a in _articles().values() if not category or a["category"] == category]
    words = _words(query)
    if not words:
        return [
            {"slug": a["slug"], "title": a["title"], "category": a["category"]}
            for a in items[: max(limit, 1)]
        ]
    scored = []
    for a in items:
        title_words = set(_words(a["title"])) | {t.lower() for t in a["tags"]}
        body_words = _words(a["body"])
        score = sum(5 * (w in title_words) + min(body_words.count(w), 5) for w in set(words))
        if score:
            scored.append((score, a))
    scored.sort(key=lambda s: (-s[0], s[1]["slug"]))
    return [
        {
            "slug": a["slug"],
            "title": a["title"],
            "category": a["category"],
            "score": score,
            "snippet": _snippet(a["body"], words),
        }
        for score, a in scored[: max(min(limit, 10), 1)]
    ]


def get(slug: str) -> dict:
    if not SLUG_RE.match(slug):
        raise DocsError("Invalid article name. Use a slug from search_docs.")
    article = _articles().get(slug)
    if article is None:
        raise DocsError(f"No article '{slug}'. Use search_docs to find one.")
    body = article["body"]
    return {
        "slug": slug,
        "title": article["title"],
        "category": article["category"],
        "tags": article["tags"],
        "content": body[:MAX_CHARS],
        "truncated": len(body) > MAX_CHARS,
    }
