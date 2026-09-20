"""Passive voxel/isometric Pygame renderer for Symbiont World.

The simulation remains hexagonal and authoritative. This module is deliberately a
presentation transform: it consumes observer state and renders a block-like
habitat without exposing or mutating World internals.
"""
from __future__ import annotations

import math

from .camera import Camera, axial_to_world
from .environment import SmoothedCell, ambient_seed, relief_factor
from .projection import VisualOrganism
from .scene import HabitatScene, Morphology, VisualEffect, VisualRemnant


def _clamp_channel(value: float) -> int:
    return max(0, min(255, int(value)))


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(_clamp_channel(channel * factor) for channel in color)


def cell_rgb(cell: SmoothedCell, relief: float = 1.0) -> tuple[int, int, int]:
    """Block-material palette derived from continuous observed terrain state."""
    wet = cell.moisture
    fertile = cell.effective_fertility
    heat = cell.temperature
    altitude = cell.elevation
    disturbance = cell.disturbance
    hazard = cell.hazard_level

    if altitude > 0.78 and wet < 0.58:
        base = (103, 105, 94)
    elif wet < 0.18 and heat > 0.48:
        base = (151, 126, 76)
    elif wet > 0.72:
        base = (58, 111, 79)
    elif fertile > 0.64:
        base = (72, 137, 72)
    else:
        base = (91, 111, 72)

    tint = (
        1.0 + 0.05 * (heat - 0.5),
        1.0 + 0.10 * (fertile - 0.5) - 0.07 * hazard,
        1.0 + 0.08 * (wet - 0.5),
    )
    disturbance_factor = 1.0 - 0.10 * disturbance
    shade = (0.84 + 0.16 * altitude) * relief * disturbance_factor
    return tuple(
        _clamp_channel(base[i] * tint[i] * shade)
        for i in range(3)
    )


def terrain_lift(elevation: float, spacing: float) -> float:
    """Presentation-only vertical lift in world units."""
    return max(0.0, min(1.0, float(elevation))) * spacing * 0.48


def voxel_top_points(
    cx: float,
    cy: float,
    half_w: float,
    half_h: float,
    *,
    lift: float = 0.0,
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Top diamond of one voxel column: north, east, south, west."""
    surface_y = cy - lift
    return (
        (round(cx), round(surface_y - half_h)),
        (round(cx + half_w), round(surface_y)),
        (round(cx), round(surface_y + half_h)),
        (round(cx - half_w), round(surface_y)),
    )


def micro_voxel_centres(
    cx: float,
    cy: float,
    half_w: float,
    half_h: float,
    *,
    resolution: int = 3,
) -> tuple[tuple[float, float, int, int], ...]:
    """Subdivide one logical cell into a presentation-only block patch."""
    if resolution < 1:
        raise ValueError("resolution must be positive")
    sub_w = half_w / resolution
    sub_h = half_h / resolution
    offset = (resolution - 1) / 2.0
    result: list[tuple[float, float, int, int]] = []
    for u in range(resolution):
        for v in range(resolution):
            du = u - offset
            dv = v - offset
            result.append((
                cx + (du - dv) * sub_w,
                cy + (du + dv) * sub_h,
                u,
                v,
            ))
    return tuple(result)


def _heading(
    previous: tuple[float, float],
    target: tuple[float, float],
    fallback: float,
) -> float:
    dx = target[0] - previous[0]
    dy = target[1] - previous[1]
    if abs(dx) + abs(dy) < 1e-9:
        return fallback
    return math.atan2(dy, dx)


class HabitatRenderer:
    """Read-only naturalist renderer with a voxel/isometric visual language."""

    def __init__(self, pygame_module) -> None:
        self.pg = pygame_module
        self.debug_grid = False
        self._font = None
        self._small = None
        self._terrain_cache_key = None
        self._terrain_cache_surface = None

    def prepare_fonts(self) -> None:
        if self._font is None:
            self._font = self.pg.font.Font(None, 25)
            self._small = self.pg.font.Font(None, 18)

    def draw(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        now: float,
        *,
        show_hud: bool,
        frozen: bool,
        error: str | None,
        selected_id: str | None,
    ) -> int:
        self.prepare_fonts()
        width, height = screen.get_size()
        screen.fill((8, 12, 15))
        visible_count = 0

        if scene.snapshot is not None:
            bounds = camera.axial_bounds(width, height, scene.spacing)
            raw_cells = scene.visible_cells(bounds)
            cells = scene.environment.sample_keys(
                [(cell.q, cell.r) for cell in raw_cells], now
            )
            cell_map = {(cell.q, cell.r): cell for cell in cells}
            organism_ids = scene.visible_track_ids(bounds)

            self._draw_cached_terrain(screen, scene, camera, cells)
            if camera.lod != "far":
                self._draw_ecology(screen, scene, camera, cells, now)
            self._draw_remnants(screen, scene, scene.remnants, camera, now, cell_map)
            visible_count = self._draw_organisms(
                screen,
                scene,
                camera,
                now,
                selected_id,
                organism_ids,
                cell_map,
            )
            self._draw_effects(screen, scene.effects, camera, now)

        if show_hud:
            self._draw_hud(
                screen,
                scene,
                camera,
                visible_count,
                frozen,
                error,
                selected_id,
            )
        return visible_count

    def _draw_cached_terrain(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        cells: list[SmoothedCell],
    ) -> None:
        width, height = screen.get_size()
        tick = scene.snapshot.tick if scene.snapshot is not None else -1
        key = (
            tick,
            width,
            height,
            round(camera.x * camera.zoom / 3.0),
            round(camera.y * camera.zoom / 3.0),
            round(camera.zoom, 3),
            self.debug_grid,
        )
        if self._terrain_cache_key != key or self._terrain_cache_surface is None:
            terrain = self.pg.Surface((width, height))
            terrain.fill((8, 12, 15))
            self._draw_voxel_terrain(terrain, scene, camera, cells)
            self._terrain_cache_surface = terrain
            self._terrain_cache_key = key
        screen.blit(self._terrain_cache_surface, (0, 0))

    def _draw_voxel_terrain(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        cells: list[SmoothedCell],
    ) -> None:
        if not cells:
            return

        width, height = screen.get_size()
        z = camera.zoom
        macro_half_w = scene.spacing * 0.70 * z
        macro_half_h = scene.spacing * 0.36 * z
        resolution = 3
        sub_half_w = macro_half_w / resolution
        sub_half_h = macro_half_h / resolution
        cell_map = {(cell.q, cell.r): cell for cell in cells}

        ordered = sorted(
            cells,
            key=lambda cell: (
                axial_to_world(cell.q, cell.r, scene.spacing)[1],
                axial_to_world(cell.q, cell.r, scene.spacing)[0],
            ),
        )

        for cell in ordered:
            wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
            if not camera.visible(
                wx,
                wy,
                width,
                height,
                margin=scene.spacing * z * 2.2,
            ):
                continue

            sx, sy = camera.world_to_screen(wx, wy, width, height)
            lift = terrain_lift(cell.elevation, scene.spacing) * z
            relief = relief_factor(cell, cell_map)
            base_color = cell_rgb(cell, relief)
            depth = max(
                3,
                round(
                    scene.spacing
                    * z
                    * (0.055 + 0.13 * cell.elevation)
                ),
            )

            for mx, my, u, v in micro_voxel_centres(
                sx,
                sy - lift,
                macro_half_w,
                macro_half_h,
                resolution=resolution,
            ):
                seed = ambient_seed(cell.q * 17 + u, cell.r * 17 + v, 901)
                variation = 0.91 + 0.16 * seed
                top_color = _shade(base_color, variation)
                top = voxel_top_points(
                    mx,
                    my,
                    sub_half_w + 1,
                    sub_half_h + 1,
                )
                _, east, south, west = top
                east_low = (east[0], east[1] + depth)
                south_low = (south[0], south[1] + depth)
                west_low = (west[0], west[1] + depth)

                self.pg.draw.polygon(
                    screen,
                    _shade(top_color, 0.50),
                    (west, south, south_low, west_low),
                )
                self.pg.draw.polygon(
                    screen,
                    _shade(top_color, 0.64),
                    (south, east, east_low, south_low),
                )
                self.pg.draw.polygon(screen, top_color, top)

                if cell.surface_water > 0.025:
                    self._draw_water_tile(
                        screen,
                        top,
                        cell.surface_water,
                        camera.zoom,
                    )

            if self.debug_grid:
                macro_top = voxel_top_points(
                    sx,
                    sy,
                    macro_half_w,
                    macro_half_h,
                    lift=lift,
                )
                self.pg.draw.polygon(
                    screen,
                    (125, 136, 138),
                    macro_top,
                    max(1, round(z)),
                )

    def _draw_water_tile(
        self,
        screen,
        top: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]],
        amount: float,
        zoom: float,
    ) -> None:
        """Block-game water surface without per-cell full-screen alpha buffers."""
        cx = sum(point[0] for point in top) / 4.0
        cy = sum(point[1] for point in top) / 4.0
        shrink = 0.87
        water = tuple(
            (
                round(cx + (x - cx) * shrink),
                round(cy + (y - cy) * shrink - 2 * zoom),
            )
            for x, y in top
        )
        # Amount changes luminance/saturation rather than transparency, keeping
        # the renderer cheap when hundreds of wet cells are visible.
        color = (
            _clamp_channel(53 + 24 * amount),
            _clamp_channel(119 + 36 * amount),
            _clamp_channel(151 + 48 * amount),
        )
        self.pg.draw.polygon(screen, color, water)
        wn, we, _, ww = water
        p1 = (
            round(ww[0] * 0.62 + wn[0] * 0.38),
            round(ww[1] * 0.62 + wn[1] * 0.38),
        )
        p2 = (
            round(wn[0] * 0.38 + we[0] * 0.62),
            round(wn[1] * 0.38 + we[1] * 0.62),
        )
        self.pg.draw.line(
            screen,
            (185, 219, 226),
            p1,
            p2,
            max(1, round(zoom)),
        )

    def _surface_screen_position(
        self,
        scene: HabitatScene,
        camera: Camera,
        cell: SmoothedCell,
        width: int,
        height: int,
    ) -> tuple[float, float]:
        wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
        sx, sy = camera.world_to_screen(wx, wy, width, height)
        return sx, sy - terrain_lift(cell.elevation, scene.spacing) * camera.zoom

    def _draw_ecology(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        cells: list[SmoothedCell],
        now: float,
    ) -> None:
        """Decorate blocks from real ecology without drawing the topology."""
        width, height = screen.get_size()
        overlay = self.pg.Surface((width, height), self.pg.SRCALPHA)
        z = camera.zoom

        for cell in cells:
            wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
            if not camera.visible(wx, wy, width, height, margin=100):
                continue
            sx, sy = self._surface_screen_position(
                scene, camera, cell, width, height
            )

            # Generic material abundance: blocky sprouts/mineral stalks. It does
            # not claim that the opaque World resource is literally vegetation.
            if cell.resource_level > 0.04:
                count = min(7, 1 + int(cell.resource_level * 7))
                for i in range(count):
                    seed = ambient_seed(cell.q, cell.r, 300 + i)
                    dx = (
                        (seed * 2.0 - 1.0)
                        * scene.spacing
                        * z
                        * 0.44
                    )
                    dy = (
                        (((seed * 9.37) % 1.0) * 2.0 - 1.0)
                        * scene.spacing
                        * z
                        * 0.19
                    )
                    stem_h = max(
                        2,
                        round(
                            (3.0 + 6.0 * cell.resource_level)
                            * math.sqrt(max(z, 0.3))
                        ),
                    )
                    px, py = round(sx + dx), round(sy + dy)
                    self.pg.draw.rect(
                        overlay,
                        (126, 155, 93, 135),
                        (
                            px,
                            py - stem_h,
                            max(1, round(z)),
                            stem_h,
                        ),
                    )
                    self.pg.draw.rect(
                        overlay,
                        (174, 181, 105, 150),
                        (
                            px + max(1, round(z)),
                            py - stem_h,
                            max(1, round(2 * z)),
                            max(1, round(2 * z)),
                        ),
                    )

            # Trails are local marks, never lines between cell centres. This
            # removes the triangular lattice that dominated the old viewer.
            if cell.traces > 0.04:
                marks = min(6, 1 + int(cell.traces * 6))
                for i in range(marks):
                    seed = ambient_seed(cell.q, cell.r, 500 + i)
                    dx = (seed * 2.0 - 1.0) * scene.spacing * z * 0.33
                    dy = (((seed * 11.9) % 1.0) * 2.0 - 1.0) * scene.spacing * z * 0.14
                    px, py = round(sx + dx), round(sy + dy)
                    length = max(2, round((2 + 3 * cell.traces) * z))
                    self.pg.draw.line(
                        overlay,
                        (105, 94, 72, 35 + int(65 * cell.traces)),
                        (px - length, py),
                        (px + length, py + max(1, length // 3)),
                        max(1, round(z)),
                    )

            if cell.detritus > 0.03:
                pieces = min(7, 1 + int(cell.detritus * 7))
                for i in range(pieces):
                    seed = ambient_seed(cell.q, cell.r, 600 + i)
                    px = round(
                        sx
                        + (seed * 2.0 - 1.0)
                        * scene.spacing
                        * z
                        * 0.35
                    )
                    py = round(
                        sy
                        + (((seed * 6.7) % 1.0) * 2.0 - 1.0)
                        * scene.spacing
                        * z
                        * 0.15
                    )
                    size = max(1, round((1.5 + 2.5 * cell.detritus) * z))
                    self.pg.draw.rect(
                        overlay,
                        (96, 78, 59, 80 + int(90 * cell.detritus)),
                        (px, py, size + 1, size),
                    )

            if cell.disturbance > 0.05:
                radius = max(
                    4,
                    round(scene.spacing * z * (0.15 + 0.30 * cell.disturbance)),
                )
                self.pg.draw.ellipse(
                    overlay,
                    (198, 151, 92, 18 + int(35 * cell.disturbance)),
                    (
                        round(sx - radius),
                        round(sy - radius * 0.36),
                        radius * 2,
                        max(2, round(radius * 0.72)),
                    ),
                    max(1, round(z)),
                )

            if cell.hazard_level > 0.04:
                # Keep danger visible but atmospheric, not a red tile overlay.
                pulse = 0.5 + 0.5 * math.sin(now * 1.2 + ambient_seed(cell.q, cell.r) * math.tau)
                radius = max(3, round(scene.spacing * z * (0.13 + 0.18 * cell.hazard_level)))
                self.pg.draw.circle(
                    overlay,
                    (
                        196,
                        74,
                        67,
                        10 + int(24 * cell.hazard_level * pulse),
                    ),
                    (round(sx), round(sy - 3 * z)),
                    radius,
                    max(1, round(z)),
                )

            if camera.lod == "near":
                self._draw_ambient_particles(
                    overlay,
                    cell,
                    sx,
                    sy,
                    scene.spacing * z,
                    now,
                )

        screen.blit(overlay, (0, 0))

    def _draw_ambient_particles(
        self,
        overlay,
        cell: SmoothedCell,
        sx: float,
        sy: float,
        radius: float,
        now: float,
    ) -> None:
        activity = max(
            cell.moisture * 0.55,
            cell.disturbance,
            abs(cell.temperature - 0.5) * 0.9,
        )
        count = min(6, int(activity * 7))
        for lane in range(count):
            seed = ambient_seed(cell.q, cell.r, lane)
            angle = seed * math.tau + now * (0.05 + 0.10 * cell.disturbance)
            orbit = radius * (0.10 + 0.40 * ((seed * 7.13) % 1.0))
            drift = math.sin(now * (0.35 + seed) + seed * 12.0)
            px = sx + math.cos(angle) * orbit
            py = sy + math.sin(angle) * orbit - drift * radius * 0.10
            alpha = 16 + int(48 * activity)
            self.pg.draw.rect(
                overlay,
                (190, 204, 191, alpha),
                (round(px), round(py), 1 if radius < 55 else 2, 1 if radius < 55 else 2),
            )

    def _draw_remnants(
        self,
        screen,
        scene: HabitatScene,
        remnants: list[VisualRemnant],
        camera: Camera,
        now: float,
        cell_map: dict[tuple[int, int], SmoothedCell],
    ) -> None:
        width, height = screen.get_size()
        if camera.lod == "far":
            return
        overlay = self.pg.Surface((width, height), self.pg.SRCALPHA)
        for remnant in remnants:
            if not camera.visible(remnant.x, remnant.y, width, height, margin=60):
                continue
            sx, sy = camera.world_to_screen(remnant.x, remnant.y, width, height)
            cell = cell_map.get((remnant.organism.q, remnant.organism.r))
            if cell is not None:
                sy -= terrain_lift(cell.elevation, scene.spacing) * camera.zoom
            progress = remnant.progress(now)
            alpha = max(0, int(150 * (1.0 - progress)))
            reserve = 0.5 if remnant.organism.reserve is None else remnant.organism.reserve
            size = max(2, round((5 + 5 * reserve) * math.sqrt(max(camera.zoom, 0.25))))
            self.pg.draw.rect(
                overlay,
                (92, 83, 72, alpha),
                (
                    round(sx - size),
                    round(sy - size * 0.25),
                    size * 2,
                    max(2, round(size * 0.55)),
                ),
            )
        screen.blit(overlay, (0, 0))

    def _draw_organisms(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        now: float,
        selected_id: str | None,
        organism_ids: set[str],
        cell_map: dict[tuple[int, int], SmoothedCell],
    ) -> int:
        width, height = screen.get_size()
        visible: list[tuple[VisualOrganism, float, float, Morphology]] = []
        for item in scene.organism_positions(now, organism_ids):
            organism, wx, wy, morphology = item
            if camera.visible(wx, wy, width, height, margin=70):
                visible.append(item)

        for organism, wx, wy, morphology in visible:
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            cell = cell_map.get((organism.q, organism.r))
            if cell is not None:
                sy -= terrain_lift(cell.elevation, scene.spacing) * camera.zoom

            if camera.lod == "far":
                self.pg.draw.rect(
                    screen,
                    (105, 206, 202) if organism.alive else (84, 84, 84),
                    (round(sx - 2), round(sy - 2), 4, 4),
                )
                continue

            track = scene.tracks.get(organism.organism_id)
            heading = morphology.symmetry_offset
            if track is not None:
                heading = _heading(track.previous, track.target, heading)

            self._draw_organism(
                screen,
                organism,
                morphology,
                sx,
                sy,
                camera.zoom,
                now,
                heading,
                selected_id == organism.organism_id,
            )
        return len(visible)

    def _draw_organism(
        self,
        screen,
        organism: VisualOrganism,
        morphology: Morphology,
        sx: float,
        sy: float,
        zoom: float,
        now: float,
        heading: float,
        selected: bool,
    ) -> None:
        """Small living mob: block-readable silhouette with organic motion."""
        integrity = 0.5 if organism.integrity is None else organism.integrity
        reserve = 0.5 if organism.reserve is None else organism.reserve
        pulse = 1.0 + math.sin(now * 2.0 + morphology.pulse_phase) * 0.045
        size = max(
            4,
            round(
                (6.0 + 6.0 * reserve)
                * math.sqrt(max(zoom, 0.25))
                * morphology.core_scale
                * pulse
            ),
        )

        # Contact shadow.
        self.pg.draw.ellipse(
            screen,
            (4, 7, 8),
            (
                round(sx - size * 0.85),
                round(sy + size * 0.40),
                max(3, round(size * 1.7)),
                max(2, round(size * 0.50)),
            ),
        )

        body_color = (
            76 + int(70 * reserve),
            132 + int(95 * integrity),
            166 + int(48 * reserve),
        ) if organism.alive else (80, 82, 83)

        # The body is intentionally not a Minecraft character. It is still a
        # Symbiont, but the chunky silhouette belongs in the same visual world.
        body_rect = self.pg.Rect(
            round(sx - size * 0.65),
            round(sy - size * 0.75),
            max(4, round(size * 1.3)),
            max(4, round(size * 1.15)),
        )
        self.pg.draw.rect(screen, _shade(body_color, 0.68), body_rect)
        inner = body_rect.inflate(
            -max(2, round(size * 0.22)),
            -max(2, round(size * 0.22)),
        )
        self.pg.draw.rect(screen, body_color, inner)

        core_size = max(2, round(size * (0.25 + 0.10 * reserve)))
        core_x = sx + math.cos(heading) * size * 0.18
        core_y = sy - size * 0.20 + math.sin(heading) * size * 0.10
        self.pg.draw.rect(
            screen,
            (211, 234, 230),
            (
                round(core_x - core_size / 2),
                round(core_y - core_size / 2),
                core_size,
                core_size,
            ),
        )

        if zoom >= 0.65:
            arms = min(organism.senses_count, 12)
            for arm in range(arms):
                angle = (
                    heading
                    + morphology.symmetry_offset
                    + math.tau * arm / max(arms, 1)
                    + math.sin(now * 0.75 + arm) * 0.06
                )
                length = size * (0.75 + 0.18 * morphology.appendage_scale)
                start = (
                    sx + math.cos(angle) * size * 0.45,
                    sy - size * 0.12 + math.sin(angle) * size * 0.35,
                )
                end = (
                    sx + math.cos(angle) * length,
                    sy - size * 0.12 + math.sin(angle) * length * 0.58,
                )
                self.pg.draw.line(
                    screen,
                    (112, 191, 194),
                    (round(start[0]), round(start[1])),
                    (round(end[0]), round(end[1])),
                    max(1, round(zoom)),
                )

        if organism.recent_damage > 0:
            self.pg.draw.rect(
                screen,
                (229, 103, 95),
                body_rect.inflate(4, 4),
                max(1, round(zoom)),
            )
        if selected:
            self.pg.draw.ellipse(
                screen,
                (236, 202, 105),
                (
                    round(sx - size),
                    round(sy + size * 0.28),
                    size * 2,
                    max(3, round(size * 0.65)),
                ),
                2,
            )

    def _draw_effects(
        self,
        screen,
        effects: list[VisualEffect],
        camera: Camera,
        now: float,
    ) -> None:
        width, height = screen.get_size()
        overlay = self.pg.Surface((width, height), self.pg.SRCALPHA)
        for effect in effects:
            if not camera.visible(effect.x, effect.y, width, height, margin=100):
                continue
            sx, sy = camera.world_to_screen(effect.x, effect.y, width, height)
            p = effect.progress(now)
            fade = max(0, int(170 * (1.0 - p)))
            radius = max(
                3,
                round(
                    (7 + 28 * p * effect.strength)
                    * math.sqrt(max(camera.zoom, 0.2))
                ),
            )
            if effect.kind == "shock":
                color = (235, 100, 95, fade)
            elif effect.kind == "absorb":
                color = (214, 195, 133, fade)
            elif effect.kind == "collapse":
                color = (150, 150, 155, fade)
            elif effect.kind == "emerge":
                color = (110, 216, 198, fade)
            elif effect.kind == "recover":
                color = (103, 210, 151, fade)
            else:
                color = (169, 190, 198, fade // 2)
            self.pg.draw.rect(
                overlay,
                color,
                (
                    round(sx - radius),
                    round(sy - radius * 0.38),
                    radius * 2,
                    max(2, round(radius * 0.76)),
                ),
                max(1, round(2 * camera.zoom)),
            )
        screen.blit(overlay, (0, 0))

    def _draw_hud(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        visible_count: int,
        frozen: bool,
        error: str | None,
        selected_id: str | None,
    ) -> None:
        snapshot = scene.snapshot
        tick = snapshot.tick if snapshot else "—"
        total = len(snapshot.organisms) if snapshot else 0
        lines = [
            (
                f"World · tick {tick} · visible {visible_count}/{total} · "
                f"remnants {len(scene.remnants)} · voxel habitat · LOD {camera.lod}"
            ),
            (
                "WASD/arrows pan   +/- zoom   F/TAB follow   R fit world   "
                "G logical grid   H HUD   SPACE freeze   ESC quit"
            ),
        ]
        if selected_id:
            lines.append(f"Following {selected_id}")
        if frozen:
            lines.append("VIEW FROZEN — World continues running")
        if error:
            lines.append(f"Disconnected: {error}")
        for i, line in enumerate(lines):
            font = self._font if i == 0 else self._small
            surface = font.render(line, True, (221, 231, 237))
            screen.blit(surface, (18, 16 + i * 22))
