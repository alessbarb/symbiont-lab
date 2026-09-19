"""Loopback-only read client for passive World visualization."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen


_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def validate_loopback_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK:
        raise ValueError("viewer accepts only local HTTP Observatory URLs")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Observatory URL must not contain credentials")


def _json_get(url: str, timeout: float) -> dict[str, Any]:
    validate_loopback_url(url)
    with urlopen(url, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise RuntimeError(f"Observatory returned HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Observatory response must be a JSON object")
    return payload


@dataclass
class WorldObserverClient:
    state_url: str = "http://127.0.0.1:8766/world/state"
    timeout: float = 1.5
    event_cursor: str | None = None

    def __post_init__(self) -> None:
        validate_loopback_url(self.state_url)

    @property
    def events_url(self) -> str:
        parsed = urlparse(self.state_url)
        host = f"[{parsed.hostname}]" if parsed.hostname == "::1" else parsed.hostname
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"http://{host}{port}/world/events"

    def fetch_state(self) -> dict[str, Any]:
        return _json_get(self.state_url, self.timeout)

    def fetch_events(self, *, limit: int = 256) -> list[dict[str, Any]]:
        query: dict[str, str] = {"limit": str(max(1, min(int(limit), 2048)))}
        if self.event_cursor:
            query["after"] = self.event_cursor
        try:
            payload = _json_get(f"{self.events_url}?{urlencode(query)}", self.timeout)
        except HTTPError as exc:
            if exc.code != 400 or self.event_cursor is None:
                raise
            # Journal retention may invalidate an old cursor. Resetting only
            # the observer cursor cannot affect World and lets the viewer heal.
            self.event_cursor = None
            payload = _json_get(f"{self.events_url}?limit={query['limit']}", self.timeout)
        events = payload.get("events", [])
        if not isinstance(events, list):
            return []
        cursor = payload.get("next_after")
        if cursor is None or isinstance(cursor, str):
            self.event_cursor = cursor
        return [item for item in events if isinstance(item, dict)]
