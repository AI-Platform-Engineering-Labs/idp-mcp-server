import pytest


@pytest.fixture(autouse=True)
def no_backstage_by_default(monkeypatch):
    # Unit tests use the catalog file unless a test fakes Backstage explicitly.
    monkeypatch.delenv("BACKSTAGE_URL", raising=False)
    monkeypatch.delenv("BACKSTAGE_TOKEN", raising=False)
