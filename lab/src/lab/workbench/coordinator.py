"""Single authority for mutually exclusive workbench run ownership."""

from __future__ import annotations

from threading import Lock


class RunCoordinator:
    def __init__(self) -> None:
        self._lock = Lock()
        self._active: str | None = None

    def acquire(self, kind: str) -> bool:
        with self._lock:
            if self._active is not None:
                return False
            self._active = str(kind)
            return True

    def release(self, kind: str) -> None:
        with self._lock:
            if self._active == kind:
                self._active = None

    @property
    def active(self) -> str | None:
        with self._lock:
            return self._active

    def payload(self) -> dict[str, object]:
        return {"active": self.active}
