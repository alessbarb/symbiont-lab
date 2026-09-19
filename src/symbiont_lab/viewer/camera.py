"""Camera and world-coordinate helpers for the Pygame habitat."""
from __future__ import annotations

import math
from dataclasses import dataclass


def axial_to_world(q: float, r: float, spacing: float = 1.0) -> tuple[float, float]:
    return (
        spacing * math.sqrt(3.0) * (q + r / 2.0),
        spacing * 1.5 * r,
    )


@dataclass
class Camera:
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    min_zoom: float = 0.18
    max_zoom: float = 4.0

    def world_to_screen(self, wx: float, wy: float, width: int, height: int) -> tuple[float, float]:
        return (
            (wx - self.x) * self.zoom + width / 2.0,
            (wy - self.y) * self.zoom + height / 2.0,
        )

    def pan_pixels(self, dx: float, dy: float) -> None:
        self.x -= dx / max(self.zoom, 1e-9)
        self.y -= dy / max(self.zoom, 1e-9)

    def zoom_by(self, factor: float) -> None:
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))

    def center_on(self, wx: float, wy: float) -> None:
        self.x = wx
        self.y = wy

    def visible(self, wx: float, wy: float, width: int, height: int, margin: float = 80.0) -> bool:
        sx, sy = self.world_to_screen(wx, wy, width, height)
        return -margin <= sx <= width + margin and -margin <= sy <= height + margin

    @property
    def lod(self) -> str:
        if self.zoom < 0.42:
            return "far"
        if self.zoom < 0.9:
            return "mid"
        return "near"
