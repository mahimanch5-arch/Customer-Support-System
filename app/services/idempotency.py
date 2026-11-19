"""In-memory idempotency store for mutating operations (refunds, cancellations).

Production note: replace with a shared TTL store (e.g. Redis) so idempotency
holds across replicas. The interface stays the same.
"""
from __future__ import annotations

import threading
import time
from typing import Any

_LOCK = threading.Lock()
_STORE: dict[str, tuple[float, Any]] = {}
_TTL_SECONDS = 24 * 3600


def _compound(principal: str, scope: str, key: str) -> str:
    return f"{principal}|{scope}|{key}"


def get(principal: str, scope: str, key: str) -> Any | None:
    now = time.time()
    with _LOCK:
        entry = _STORE.get(_compound(principal, scope, key))
        if not entry:
            return None
        ts, value = entry
        if now - ts > _TTL_SECONDS:
            _STORE.pop(_compound(principal, scope, key), None)
            return None
        return value


def put(principal: str, scope: str, key: str, value: Any) -> None:
    with _LOCK:
        _STORE[_compound(principal, scope, key)] = (time.time(), value)
