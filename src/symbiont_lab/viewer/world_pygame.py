"""Passive Pygame viewer for the persistent Symbiont World.

The viewer is deliberately out-of-process: it consumes Observatory's read-only
/world/state endpoint and never imports the World runtime, calls WorldAction, or
owns simulation time. Pausing here freezes only rendering, never the world.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


DEFAULT_STATE_URL = "http://127.0.0.1:8766/world/state"


@dataclass(frozen=True)
class VisualCell:
    q: int
    r: int
    elevation: float
    moisture: float
    temperature: float
    fertility: float
    traces: float
    disturbance: float
    resource_level: float
    hazard_level: float


@dataclass(frozen=True)
class VisualOrganism:
    organism_id: str
    q: int
    r: int
    alive: bool
    integrity: float | None
    reserve: float | None
    senses_count: int


def _bounded(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(0.0, min(1.0, number))


def project_snapshot(snapshot: dict[str, Any]) -> tuple[list[VisualCell], list[VisualOrganism]]:
    """Project observer state into renderer primitives without semantic labels."""
    cells: list[VisualCell] = []
    raw_cells = snapshot.get("cells", {})
    if isinstance(raw_cells, dict):
        for payload in raw_cells.values():
            if not isinstance(payload, dict):
                continue
            resources = payload.get("resources", {})
            capacities = payload.get("resource_capacities", {})
            fractions: list[float] = []
            if isinstance(resources, dict) and isinstance(capacities, dict):
                for key, quantity in resources.items():
                    try:
                        capacity = float(capacities.get(key, 0.0))
                        amount = float(quantity)
                    except (TypeError, ValueError):
                        continue
                    if capacity > 0.0 and math.isfinite(capacity) and math.isfinite(amount):
                        fractions.append(max(0.0, min(1.0, amount / capacity)))
            hazards = payload.get("hazards", {})
            hazard_values = [
                _bounded(value)
                for value in hazards.values()
            ] if isinstance(hazards, dict) else []
            cells.append(
                VisualCell(
                    q=int(payload.get("q", 0)),
                    r=int(payload.get("r", 0)),
                    elevation=_bounded(payload.get("elevation"), 0.5),
                    moisture=_bounded(payload.get("moisture"), 0.5),
                    temperature=_bounded(payload.get("temperature"), 0.5),
                    fertility=_bounded(payload.get("fertility"), 0.5),
                    traces=_bounded(payload.get("traces")),
                    disturbance=_bounded(payload.get("disturbance")),
                    resource_level=sum(fractions) / len(fractions) if fractions else 0.0,
                    hazard_level=max(hazard_values) if hazard_values else 0.0,
                )
            )

    organisms: list[VisualOrganism] = []
    raw_organisms = snapshot.get("organisms", [])
    if isinstance(raw_organisms, list):
        for payload in raw_organisms:
            if not isinstance(payload, dict):
                continue
            organisms.append(
                VisualOrganism(
                    organism_id=str(payload.get("id", "?")),
                    q=int(payload.get("q", 0)),
                    r=int(payload.get("r", 0)),
                    alive=bool(payload.get("alive", True)),
                    integrity=None if payload.get("integrity") is None else _bounded(payload.get("integrity")),
                    reserve=None if payload.get("metabolic_reserve") is None else _bounded(payload.get("metabolic_reserve")),
                    senses_count=max(0, int(payload.get("senses_count", 0) or 0)),
                )
            )
    return cells, organisms


def fetch_snapshot(url: str, timeout: float = 1.5) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise RuntimeError(f"Observatory returned HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("World state must be a JSON object")
    return payload


def _hex_center(q: int, r: int, radius: float) -> tuple[float, float]:
    # Pointy-top axial coordinates.
    return (
        radius * math.sqrt(3.0) * (q + r / 2.0),
        radius * 1.5 * r,
    )


def _hex_points(cx: float, cy: float, radius: float) -> list[tuple[int, int]]:
    return [
        (
            round(cx + radius * math.cos(math.radians(60 * i - 30))),
            round(cy + radius * math.sin(math.radians(60 * i - 30))),
        )
        for i in range(6)
    ]


def _cell_rgb(cell: VisualCell) -> tuple[int, int, int]:
    # Appearance derives from physical properties, not semantic resource names.
    altitude = cell.elevation
    wet = cell.moisture
    fertile = cell.fertility
    heat = cell.temperature
    hazard = cell.hazard_level
    r = 30 + int(70 * heat) + int(70 * hazard)
    g = 35 + int(95 * fertile) + int(35 * wet) - int(45 * hazard)
    b = 45 + int(90 * wet) - int(30 * heat)
    shade = 0.72 + 0.28 * altitude
    return tuple(max(0, min(255, int(channel * shade))) for channel in (r, g, b))


def run(url: str = DEFAULT_STATE_URL, *, fps: int = 60, poll_hz: float = 8.0) -> int:
    try:
        import pygame
    except ImportError as exc:
        raise SystemExit(
            "Pygame viewer is optional. Install with: pip install 'symbiont-lab[viewer]'"
        ) from exc

    pygame.init()
    screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    pygame.display.set_caption("Symbiont World — Naturalist View")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    small = pygame.font.Font(None, 18)

    running = True
    visual_paused = False
    show_hud = True
    zoom = 1.0
    pan_x = 70.0
    pan_y = 80.0
    follow_index: int | None = None
    last_poll = 0.0
    snapshot: dict[str, Any] = {}
    cells: list[VisualCell] = []
    organisms: list[VisualOrganism] = []
    error: str | None = None

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    visual_paused = not visual_paused
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    zoom = min(3.5, zoom * 1.12)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    zoom = max(0.35, zoom / 1.12)
                elif event.key == pygame.K_h:
                    show_hud = not show_hud
                elif event.key == pygame.K_f:
                    if organisms:
                        follow_index = 0 if follow_index is None else (follow_index + 1) % len(organisms)
                elif event.key == pygame.K_TAB:
                    if organisms:
                        follow_index = 0 if follow_index is None else (follow_index + 1) % len(organisms)

        keys = pygame.key.get_pressed()
        speed = 360.0 / max(zoom, 0.1) / fps
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            pan_x += speed
            follow_index = None
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            pan_x -= speed
            follow_index = None
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            pan_y += speed
            follow_index = None
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            pan_y -= speed
            follow_index = None

        now = time.monotonic()
        if not visual_paused and now - last_poll >= 1.0 / max(poll_hz, 0.25):
            last_poll = now
            try:
                snapshot = fetch_snapshot(url)
                cells, organisms = project_snapshot(snapshot)
                error = None
            except (OSError, URLError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                error = str(exc)

        width, height = screen.get_size()
        screen.fill((5, 10, 16))

        radius = 30.0 * zoom
        if follow_index is not None and organisms:
            follow_index %= len(organisms)
            target = organisms[follow_index]
            tx, ty = _hex_center(target.q, target.r, radius)
            pan_x = width / 2.0 - tx
            pan_y = height / 2.0 - ty

        for cell in cells:
            x, y = _hex_center(cell.q, cell.r, radius)
            cx, cy = x + pan_x, y + pan_y
            if cx < -radius or cy < -radius or cx > width + radius or cy > height + radius:
                continue
            pygame.draw.polygon(screen, _cell_rgb(cell), _hex_points(cx, cy, radius - 1))
            if cell.resource_level > 0.02:
                size = max(2, int(2 + 7 * cell.resource_level * zoom))
                pygame.draw.circle(screen, (180, 215, 130), (round(cx), round(cy)), size)
            if cell.hazard_level > 0.02:
                ring = max(4, int(radius * (0.25 + 0.35 * cell.hazard_level)))
                pygame.draw.circle(screen, (205, 92, 92), (round(cx), round(cy)), ring, max(1, int(2 * zoom)))
            if cell.traces > 0.03:
                trail_radius = max(2, int(radius * 0.12 * cell.traces))
                pygame.draw.circle(screen, (150, 150, 165), (round(cx - radius * .25), round(cy + radius * .2)), trail_radius)

        for index, org in enumerate(organisms):
            x, y = _hex_center(org.q, org.r, radius)
            cx, cy = x + pan_x, y + pan_y
            if not (-40 <= cx <= width + 40 and -40 <= cy <= height + 40):
                continue
            integrity = org.integrity if org.integrity is not None else 0.5
            reserve = org.reserve if org.reserve is not None else 0.5
            body_radius = max(5, int((7 + 8 * reserve) * math.sqrt(zoom)))
            body_color = (92 + int(80 * reserve), 190 + int(45 * integrity), 205)
            if not org.alive:
                body_color = (95, 100, 108)
            pygame.draw.circle(screen, body_color, (round(cx), round(cy)), body_radius)
            pygame.draw.circle(screen, (225, 240, 245), (round(cx), round(cy)), body_radius + 3, 1)
            antennae = min(org.senses_count, 12)
            for arm in range(antennae):
                angle = (2 * math.pi * arm / max(antennae, 1)) + (snapshot.get("tick", 0) % 30) * 0.01
                end = (
                    round(cx + math.cos(angle) * (body_radius + 4 + 4 * zoom)),
                    round(cy + math.sin(angle) * (body_radius + 4 + 4 * zoom)),
                )
                pygame.draw.line(screen, (125, 210, 225), (round(cx), round(cy)), end, 1)
            if follow_index == index:
                pygame.draw.circle(screen, (245, 215, 120), (round(cx), round(cy)), body_radius + 9, 2)

        if show_hud:
            tick = snapshot.get("tick", "—")
            alive = snapshot.get("alive_count", len([o for o in organisms if o.alive]))
            lines = [
                f"World  tick {tick}   population {alive}",
                "ESC quit   SPACE freeze view   +/- zoom   arrows/WASD pan   F/TAB follow   H HUD",
                "Viewer is passive: pausing or moving the camera never pauses or controls World.",
            ]
            if visual_paused:
                lines.append("VIEW FROZEN — World continues running")
            if error:
                lines.append(f"Disconnected: {error}")
            for i, line in enumerate(lines):
                surface = (font if i == 0 else small).render(line, True, (220, 232, 240))
                screen.blit(surface, (18, 16 + i * 23))

        pygame.display.flip()
        clock.tick(max(15, fps))

    pygame.quit()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Passive naturalist Pygame view of Symbiont World")
    parser.add_argument("--url", default=DEFAULT_STATE_URL, help="Observatory /world/state URL")
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--poll-hz", type=float, default=8.0)
    args = parser.parse_args(argv)
    return run(args.url, fps=args.fps, poll_hz=args.poll_hz)


if __name__ == "__main__":
    raise SystemExit(main())
