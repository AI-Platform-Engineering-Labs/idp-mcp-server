"""Loads the service catalog (catalog/services.yaml) that stands in for a real IDP."""

import os
from pathlib import Path

import yaml

DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "catalog" / "services.yaml"


def catalog_path() -> Path:
    return Path(os.environ.get("CATALOG_PATH", DEFAULT_CATALOG))


def load_services() -> list[dict]:
    with catalog_path().open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("services", [])
