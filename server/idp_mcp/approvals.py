"""Human approval for write actions.

An agent can ask for a write action (e.g. create_service) but never performs it. The request
waits here until a human approves or denies it through the admin endpoint
(POST /admin/approvals/<id>/approve, see server.py and scripts/approve.sh).

Requests live in memory: fine for a single-replica demo, and a restart clears them. A real
platform would keep them in a database or ticket system and write an audit log.
"""

import logging
import threading
import uuid
from datetime import UTC, datetime

log = logging.getLogger("idp_mcp.audit")

_lock = threading.Lock()
_requests: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def create(action: str, params: dict) -> dict:
    request = {
        "id": f"req-{uuid.uuid4().hex[:8]}",
        "action": action,
        "params": params,
        "status": "pending_approval",
        "requested_at": _now(),
        "decided_at": None,
        "result": None,
    }
    with _lock:
        _requests[request["id"]] = request
    log.info("approval requested id=%s action=%s params=%s", request["id"], action, params)
    return dict(request)


def get(request_id: str) -> dict | None:
    with _lock:
        request = _requests.get(request_id)
        return dict(request) if request else None


def pending() -> list[dict]:
    with _lock:
        return [dict(r) for r in _requests.values() if r["status"] == "pending_approval"]


def decide(request_id: str, approve: bool) -> dict | None:
    """Approve or deny a pending request. None if it is unknown or already decided."""
    with _lock:
        request = _requests.get(request_id)
        if request is None or request["status"] != "pending_approval":
            return None
        request["status"] = "approved" if approve else "denied"
        request["decided_at"] = _now()
        if approve:
            request["result"] = _execute(request["action"], request["params"])
        log.info("approval %s id=%s action=%s", request["status"], request_id, request["action"])
        return dict(request)


def _execute(action: str, params: dict) -> dict:
    # The approval flow above is real. The action itself is a placeholder in this demo:
    # a real platform would call the Backstage scaffolder here.
    return {
        "executed": action,
        "note": "Demo placeholder: approved, but no repository was actually created.",
        "params": params,
    }


def clear() -> None:
    """Forget everything (used by tests)."""
    with _lock:
        _requests.clear()
