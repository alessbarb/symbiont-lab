"""Camera and world-coordinate helpers for the Pygame habitat."""
from __future__ import annotations

import math
from dataclasses import dataclass


def axial_to_world(q: float, r: float, spacing: float = 1.0) -> tuple[float, float]:
    return (
        spacing * math.sqrt(3.0) * (q + r / 2.0),
        spacing * 1.5 * r,
    )


def world_to_axial(x: float, y: float, spacing: float = 1.0) -> tuple[float, float]:
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    q = (math.sqrt(3.0) / 3.0 * x - y / 3.0) / spacing
    r = (2.0 / 3.0 * y) / spacing
    return q, r


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

    def screen_to_world(self, sx: float, sy: float, width: int, height: int) -> tuple[float, float]:
        return (
            (sx - width / 2.0) / max(self.zoom, 1e-9) + self.x,
            (sy - height / 2.0) / max(self.zoom, 1e-9) + self.y,
        )

    def axial_bounds(
        self,
        width: int,
        height: int,
        spacing: float,
        *,
        margin_pixels: float = 120.0,
    ) -> tuple[int, int, int, int]:
        corners = [
            self.screen_to_world(-margin_pixels, -margin_pixels, width, height),
            self.screen_to_world(width + margin_pixels, -margin_pixels, width, height),
            self.screen_to_world(-margin_pixels, height + margin_pixels, width, height),
            self.screen_to_world(width + margin_pixels, height + margin_pixels, width, height),
        ]
        axial = [world_to_axial(x, y, spacing) for x, y in corners]
        qs = [q for q, _ in axial]
        rs = [rr for _, rr in axial]
        pad = 2
        return (
            math.floor(min(qs)) - pad,
            math.ceil(max(qs)) + pad,
            math.floor(min(rs)) - pad,
            math.ceil(max(rs)) + pad,
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
