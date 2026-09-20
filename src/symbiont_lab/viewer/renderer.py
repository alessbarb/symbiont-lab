"""Pygame ecosystem renderer.

Consumes only projected observer state. It never imports World. The logical World
remains hexagonal, but the default presentation deliberately renders it as a
continuous habitat. Hex boundaries are available only through debug_grid.
"""
from __future__ import annotations

import math

from .camera import Camera, axial_to_world
from .environment import SmoothedCell, ambient_seed, relief_factor
from .projection import VisualOrganism
from .scene import HabitatScene, Morphology, VisualEffect, VisualRemnant


def cell_rgb(cell: SmoothedCell, relief: float = 1.0) -> tuple[int, int, int]:
    """Naturalistic terrain colour derived only from observed physical fields."""
    altitude = cell.elevation
    wet = cell.moisture
    fertile = cell.effective_fertility
    heat = cell.temperature
    hazard = cell.hazard_level
    disturbance = cell.disturbance

    # Keep the palette deliberately muted: ecology should read as terrain, not
    # as a categorical heatmap. Hazards/disturbance tint the substrate without
    # turning cells into semantic coloured tiles.
    r = 31 + int(46 * heat) + int(24 * hazard) + int(18 * disturbance)
    g = 39 + int(92 * fertile) + int(31 * wet) - int(22 * hazard)
    b = 42 + int(69 * wet) - int(18 * heat) + int(10 * altitude)
    shade = (0.78 + 0.22 * altitude) * relief
    return tuple(max(0, min(255, int(channel * shade))) for channel in (r, g, b))


def _hex_points(cx: float, cy: float, radius: float) -> list[tuple[int, int]]:
    return [
        (
            round(cx + radius * math.cos(math.radians(60 * i - 30))),
            round(cy + radius * math.sin(math.radians(60 * i - 30))),
        )
        for i in range(6)
    ]


def _mean_rgb(colors: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not colors:
        return (22, 31, 34)
    count = len(colors)
    return tuple(sum(color[channel] for color in colors) // count for channel in range(3))


def _heading(previous: tuple[float, float], target: tuple[float, float], fallback: float) -> float:
    dx = target[0] - previous[0]
    dy = target[1] - previous[1]
    if abs(dx) + abs(dy) < 1e-9:
        return fallback
    return math.atan2(dy, dx)


class HabitatRenderer:
    def __init__(self, pygame_module) -> None:
        self.pg = pygame_module
        self.debug_grid = False
        self._font = None
        self._small = None

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
        screen.fill((6, 10, 13))
        visible_count = 0

        snapshot = scene.snapshot
        if snapshot is not None:
            bounds = camera.axial_bounds(width, height, scene.spacing)
            raw_cells = scene.visible_cells(bounds)
            cells = scene.environment.sample_keys([(cell.q, cell.r) for cell in raw_cells], now)
            organism_ids = scene.visible_track_ids(bounds)
            self._draw_terrain(screen, scene, camera, cells)
            self._draw_environment(screen, scene, camera, cells, now)
            self._draw_remnants(screen, scene.remnants, camera, now)
            visible_count = self._draw_organisms(screen, scene, camera, now, selected_id, organism_ids)
            self._draw_effects(screen, scene.effects, camera, now)

        if show_hud:
            self._draw_hud(screen, scene, camera, visible_count, frozen, error, selected_id)
        return visible_count

    def _draw_terrain(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        cells: list[SmoothedCell],
    ) -> None:
        """Render the discrete substrate as a continuous visual field.

        The equal-colour footprint hides internal cell boundaries. Overlapping
        translucent radial patches then blend neighbouring physical states into
        an organic terrain. The real hex lattice is drawn only in debug mode.
        """
        if not cells:
            return

        width, height = screen.get_size()
        z = camera.zoom
        hex_radius = scene.spacing * 1.06 * z
        field_radius = max(5.0, scene.spacing * 1.52 * z)
        cell_map = {(cell.q, cell.r): cell for cell in cells}

        colors = [
            cell_rgb(cell, relief_factor(cell, cell_map))
            for cell in cells
        ]
        base = _mean_rgb(colors)
        footprint = (
            max(0, int(base[0] * 0.70)),
            max(0, int(base[1] * 0.70)),
            max(0, int(base[2] * 0.70)),
        )

        # The footprint defines world extent but has no per-cell colour, so no
        # honeycomb can be perceived in normal mode.
        for cell in cells:
            wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
            if not camera.visible(wx, wy, width, height, margin=hex_radius * 2):
                continue
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            self.pg.draw.polygon(
                screen,
                footprint,
                _hex_points(sx, sy, hex_radius + 2.0),
            )

        # Blend physical state between neighbouring centres. Each patch is a
        # small alpha surface, so overlap is genuinely composited by Pygame.
        for cell, color in zip(cells, colors):
            wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
            if not camera.visible(wx, wy, width, height, margin=field_radius * 2):
                continue
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            radius = int(max(4, round(field_radius)))
            diameter = radius * 2 + 2
            blot = self.pg.Surface((diameter, diameter), self.pg.SRCALPHA)
            centre = (radius + 1, radius + 1)

            # Broad low-opacity falloff removes tile edges while preserving
            # large-scale gradients.
            self.pg.draw.circle(blot, (*color, 38), centre, radius)
            self.pg.draw.circle(blot, (*color, 58), centre, max(2, round(radius * 0.72)))
            self.pg.draw.circle(blot, (*color, 76), centre, max(2, round(radius * 0.46)))
            screen.blit(blot, (round(sx) - radius - 1, round(sy) - radius - 1))

        self._draw_water_field(screen, scene, camera, cells)

        if self.debug_grid:
            for cell in cells:
                wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
                if not camera.visible(wx, wy, width, height, margin=hex_radius * 2):
                    continue
                sx, sy = camera.world_to_screen(wx, wy, width, height)
                self.pg.draw.polygon(
                    screen,
                    (90, 108, 116),
                    _hex_points(sx, sy, hex_radius),
                    max(1, round(z)),
                )

    def _draw_water_field(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        cells: list[SmoothedCell],
    ) -> None:
        """Draw surface water as irregular pools rather than cell-centred discs."""
        width, height = screen.get_size()
        z = camera.zoom
        overlay = self.pg.Surface((width, height), self.pg.SRCALPHA)

        for cell in cells:
            if cell.surface_water <= 0.015:
                continue
            wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
            if not camera.visible(wx, wy, width, height, margin=100):
                continue
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            strength = cell.surface_water
            base_radius = scene.spacing * z * (0.30 + 0.64 * strength)

            # Stable overlapping lobes produce a pond/catchment silhouette
            # without inventing any new World state.
            for lobe in range(5):
                seed = ambient_seed(cell.q, cell.r, 700 + lobe)
                angle = seed * math.tau
                offset = base_radius * (0.10 + 0.28 * ((seed * 7.7) % 1.0))
                radius = max(
                    2,
                    round(base_radius * (0.55 + 0.34 * ((seed * 13.1) % 1.0))),
                )
                px = round(sx + math.cos(angle) * offset)
                py = round(sy + math.sin(angle) * offset)
                self.pg.draw.circle(
                    overlay,
                    (82, 143, 164, min(112, 25 + int(95 * strength))),
                    (px, py),
                    radius,
                )

            if camera.lod == "near":
                shine = max(3, round(base_radius * 0.35))
                self.pg.draw.arc(
                    overlay,
                    (188, 221, 225, min(100, 25 + int(80 * strength))),
                    (
                        round(sx - shine),
                        round(sy - shine * 0.55),
                        shine * 2,
                        max(2, round(shine * 1.1)),
                    ),
                    math.pi * 1.05,
                    math.pi * 1.82,
                    max(1, round(z)),
                )

        screen.blit(overlay, (0, 0))

    def _draw_environment(
        self,
        screen,
        scene: HabitatScene,
        camera: Camera,
        cells: list[SmoothedCell],
        now: float,
    ) -> None:
        width, height = screen.get_size()
        if camera.lod == "far":
            return

        overlay = self.pg.Surface((width, height), self.pg.SRCALPHA)
        cell_map = {(cell.q, cell.r): cell for cell in cells}

        # Traffic is rendered as a faint continuous path between neighbouring
        # centres. The path is evidence from traces, not an exposed grid edge.
        for cell in cells:
            if cell.traces <= 0.04:
                continue
            for dq, dr in ((1, 0), (0, 1), (1, -1)):
                other = cell_map.get((cell.q + dq, cell.r + dr))
                if other is None or other.traces <= 0.04:
                    continue
                strength = min(cell.traces, other.traces)
                ax, ay = axial_to_world(cell.q, cell.r, scene.spacing)
                bx, by = axial_to_world(other.q, other.r, scene.spacing)
                asx, asy = camera.world_to_screen(ax, ay, width, height)
                bsx, bsy = camera.world_to_screen(bx, by, width, height)
                self.pg.draw.line(
                    overlay,
                    (176, 160, 135, 14 + int(64 * strength)),
                    (round(asx), round(asy)),
                    (round(bsx), round(bsy)),
                    max(1, round((2.0 + 3.5 * strength) * camera.zoom)),
                )

        for cell in cells:
            wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
            if not camera.visible(wx, wy, width, height, margin=80):
                continue
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            z = camera.zoom

            # Material abundance reads as sparse organic growth/mineral texture,
            # not as a resource icon.
            if cell.resource_level > 0.03:
                count = min(8, 1 + int(cell.resource_level * 8))
                for i in range(count):
                    seed = ambient_seed(cell.q, cell.r, 200 + i)
                    angle = seed * math.tau
                    distance = scene.spacing * z * (0.10 + 0.38 * ((seed * 5.3) % 1.0))
                    px = sx + math.cos(angle) * distance
                    py = sy + math.sin(angle) * distance
                    stem = max(2.0, (2.5 + 4.5 * cell.resource_level) * math.sqrt(z))
                    self.pg.draw.line(
                        overlay,
                        (132, 164, 116, 80 + int(75 * cell.resource_level)),
                        (round(px), round(py + stem * 0.4)),
                        (round(px), round(py - stem)),
                        max(1, round(math.sqrt(z))),
                    )
                    self.pg.draw.circle(
                        overlay,
                        (174, 180, 125, 95 + int(70 * cell.resource_level)),
                        (round(px + stem * 0.35), round(py - stem)),
                        max(1, round(stem * 0.30)),
                    )

            # Hazards remain deliberately subtle. They should be inspectable,
            # not turn the naturalist view into a red heatmap.
            if cell.hazard_level > 0.025:
                rr = max(5, round(scene.spacing * z * (0.32 + 0.52 * cell.hazard_level)))
                self.pg.draw.circle(
                    overlay,
                    (174, 72, 68, 10 + int(32 * cell.hazard_level)),
                    (round(sx), round(sy)),
                    rr,
                )

            if cell.disturbance > 0.04:
                rr = max(3, round(scene.spacing * z * (0.16 + cell.disturbance * 0.36)))
                self.pg.draw.circle(
                    overlay,
                    (209, 172, 116, 26 + int(24 * cell.disturbance)),
                    (round(sx), round(sy)),
                    rr,
                    max(1, round(z)),
                )

            if cell.detritus > 0.02:
                count = min(10, 1 + int(cell.detritus * 10))
                for i in range(count):
                    seed = ambient_seed(cell.q, cell.r, 100 + i)
                    angle = seed * math.tau
                    dist = scene.spacing * z * (0.10 + ((seed * 5.17) % 1.0) * 0.34)
                    px = round(sx + math.cos(angle) * dist)
                    py = round(sy + math.sin(angle) * dist)
                    length = max(2, round((2.0 + 3.0 * cell.detritus) * math.sqrt(z)))
                    self.pg.draw.line(
                        overlay,
                        (105, 89, 70, 38 + int(90 * cell.detritus)),
                        (px - length, py),
                        (px + length, py + max(1, length // 3)),
                        1,
                    )

            if cell.ecological_pressure > 0.03:
                rr = max(4, round(scene.spacing * z * (0.20 + 0.38 * cell.ecological_pressure)))
                self.pg.draw.circle(
                    overlay,
                    (118, 97, 76, 12 + int(28 * cell.ecological_pressure)),
                    (round(sx), round(sy)),
                    rr,
                    max(1, round(z)),
                )

            if camera.lod == "near":
                self._draw_ambient_particles(overlay, cell, sx, sy, scene.spacing * z, now)

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
            cell.moisture * 0.7,
            cell.disturbance,
            abs(cell.temperature - 0.5) * 1.1,
        )
        count = min(10, int(activity * 10))
        for lane in range(count):
            seed = ambient_seed(cell.q, cell.r, lane)
            angle = (seed * math.tau + now * (0.08 + 0.16 * cell.disturbance)) % math.tau
            orbit = radius * (0.12 + 0.55 * ((seed * 7.13) % 1.0))
            drift = math.sin(now * (0.4 + seed) + seed * 12.0)
            px = sx + math.cos(angle) * orbit
            py = sy + math.sin(angle) * orbit - drift * radius * 0.12 * (0.3 + cell.temperature)
            alpha = 18 + int(70 * activity)
            if cell.moisture >= max(cell.disturbance, abs(cell.temperature - 0.5)):
                color = (178, 205, 214, alpha)
            elif cell.disturbance >= abs(cell.temperature - 0.5):
                color = (215, 191, 154, alpha)
            else:
                color = (220, 182, 150, alpha)
            self.pg.draw.circle(
                overlay,
                color,
                (round(px), round(py)),
                1 if radius < 50 else 2,
            )

    def _draw_remnants(
        self,
        screen,
        remnants: list[VisualRemnant],
        camera: Camera,
        now: float,
    ) -> None:
        width, height = screen.get_size()
        if camera.lod == "far":
            return
        overlay = self.pg.Surface((width, height), self.pg.SRCALPHA)
        for remnant in remnants:
            if not camera.visible(remnant.x, remnant.y, width, height, margin=60):
                continue
            sx, sy = camera.world_to_screen(remnant.x, remnant.y, width, height)
            progress = remnant.progress(now)
            alpha = max(0, int(145 * (1.0 - progress)))
            reserve = 0.5 if remnant.organism.reserve is None else remnant.organism.reserve
            base = max(3.0, (6.0 + 6.0 * reserve) * math.sqrt(max(camera.zoom, 0.25)))
            rx = max(2, round(base * (1.0 + 0.4 * progress)))
            ry = max(1, round(base * (0.42 - 0.18 * progress)))
            self.pg.draw.ellipse(
                overlay,
                (92, 89, 84, alpha // 2),
                (round(sx - rx * 1.15), round(sy - ry * 0.2), round(rx * 2.3), max(2, ry)),
            )
            self.pg.draw.ellipse(
                overlay,
                (112, 105, 94, alpha),
                (round(sx - rx), round(sy - ry), rx * 2, ry * 2),
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
    ) -> int:
        width, height = screen.get_size()
        visible: list[tuple[VisualOrganism, float, float, Morphology]] = []
        for item in scene.organism_positions(now, organism_ids):
            organism, wx, wy, morphology = item
            if camera.visible(wx, wy, width, height, margin=55):
                visible.append(item)

        if camera.lod == "far":
            for organism, wx, wy, _ in visible:
                sx, sy = camera.world_to_screen(wx, wy, width, height)
                color = (105, 203, 199) if organism.alive else (82, 84, 86)
                self.pg.draw.circle(
                    screen,
                    color,
                    (round(sx), round(sy)),
                    2 if camera.zoom < .3 else 3,
                )
            return len(visible)

        for organism, wx, wy, morphology in visible:
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            track = scene.tracks.get(organism.organism_id)
            heading = morphology.symmetry_offset
            if track is not None:
                heading = _heading(track.previous, track.target, heading)
                if track.previous != track.target and camera.lod == "near":
                    psx, psy = camera.world_to_screen(
                        track.previous[0], track.previous[1], width, height
                    )
                    trail = self.pg.Surface((width, height), self.pg.SRCALPHA)
                    self.pg.draw.line(
                        trail,
                        (82, 137, 142, 42),
                        (round(psx), round(psy)),
                        (round(sx), round(sy)),
                        max(1, round(2 * camera.zoom)),
                    )
                    screen.blit(trail, (0, 0))

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
        """Render a soft-bodied digital organism oriented by real movement."""
        integrity = 0.5 if organism.integrity is None else organism.integrity
        reserve = 0.5 if organism.reserve is None else organism.reserve
        pulse = 1.0 + math.sin(now * 2.15 + morphology.pulse_phase) * 0.045
        base = max(
            4.0,
            (7.5 + 7.5 * reserve)
            * math.sqrt(max(zoom, .25))
            * morphology.core_scale
            * pulse,
        )
        if not organism.alive:
            base *= 0.84

        # Grounding shadow makes motion read as an organism travelling across a
        # surface rather than a symbol hopping between cell centres.
        shadow_w = max(4, round(base * 2.15))
        shadow_h = max(2, round(base * 0.64))
        shadow = self.pg.Surface((shadow_w + 8, shadow_h + 8), self.pg.SRCALPHA)
        self.pg.draw.ellipse(
            shadow,
            (0, 0, 0, 58),
            (4, 4, shadow_w, shadow_h),
        )
        screen.blit(
            shadow,
            (round(sx - shadow_w / 2 - 4), round(sy + base * 0.48 - shadow_h / 2 - 4)),
        )

        # Soft asymmetric silhouette. The longitudinal axis follows observed
        # displacement; stationary organisms keep a stable morphology-derived
        # orientation.
        points: list[tuple[int, int]] = []
        samples = max(18, morphology.lobes * 4)
        cos_h = math.cos(heading)
        sin_h = math.sin(heading)
        for i in range(samples):
            angle = math.tau * i / samples
            irregular = 1.0 + 0.075 * math.sin(
                angle * morphology.lobes + morphology.symmetry_offset
            )
            longitudinal = base * 1.14 * math.cos(angle) * irregular
            lateral = base * 0.76 * math.sin(angle) * irregular
            # Slightly fuller front and tapered rear.
            longitudinal *= 1.0 + 0.08 * math.cos(angle)
            px = sx + longitudinal * cos_h - lateral * sin_h
            py = sy + longitudinal * sin_h + lateral * cos_h
            points.append((round(px), round(py)))

        color = (
            72 + int(74 * reserve),
            126 + int(100 * integrity),
            161 + int(50 * reserve),
        ) if organism.alive else (78, 81, 82)
        edge = (
            max(0, color[0] - 25),
            max(0, color[1] - 25),
            max(0, color[2] - 25),
        )
        self.pg.draw.polygon(screen, edge, points)
        inner = [
            (
                round(sx + (x - sx) * 0.91),
                round(sy + (y - sy) * 0.91),
            )
            for x, y in points
        ]
        self.pg.draw.polygon(screen, color, inner)

        # Internal translucent-looking core pulse.
        core_r = max(2, round(base * (0.25 + 0.13 * reserve)))
        core_x = sx + math.cos(heading) * base * 0.16
        core_y = sy + math.sin(heading) * base * 0.16
        self.pg.draw.circle(
            screen,
            (188 + int(40 * reserve), 222, 219),
            (round(core_x), round(core_y)),
            core_r,
        )
        self.pg.draw.circle(
            screen,
            (225, 240, 238),
            (round(core_x), round(core_y)),
            max(1, round(core_r * 0.48)),
            1,
        )

        if zoom >= 0.65:
            arms = min(organism.senses_count, 16)
            for arm in range(arms):
                # Sensors distribute around the body but flex slowly instead of
                # reading as perfectly radial spokes.
                around = (
                    heading
                    + morphology.symmetry_offset
                    + math.tau * arm / max(arms, 1)
                    + math.sin(now * 0.8 + arm * 1.7 + morphology.pulse_phase) * 0.08
                )
                length = base * (
                    1.05
                    + 0.34 * morphology.appendage_scale
                    + 0.08 * math.sin(now + arm)
                )
                start = (
                    sx + math.cos(around) * base * 0.58,
                    sy + math.sin(around) * base * 0.58,
                )
                end = (
                    sx + math.cos(around) * length,
                    sy + math.sin(around) * length,
                )
                self.pg.draw.line(
                    screen,
                    (104, 181, 188),
                    (round(start[0]), round(start[1])),
                    (round(end[0]), round(end[1])),
                    1,
                )
                self.pg.draw.circle(
                    screen,
                    (145, 207, 205),
                    (round(end[0]), round(end[1])),
                    1,
                )

        if organism.recent_damage > 0:
            self.pg.draw.arc(
                screen,
                (228, 105, 96),
                (
                    round(sx - base * 1.22),
                    round(sy - base * 1.22),
                    round(base * 2.44),
                    round(base * 2.44),
                ),
                heading - 0.8,
                heading + 0.8,
                max(1, round(zoom)),
            )
        if selected:
            self.pg.draw.circle(
                screen,
                (236, 203, 108),
                (round(sx), round(sy)),
                round(base + 9),
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
            fade = max(0, int(180 * (1.0 - p)))
            radius = max(
                3,
                round(
                    (8 + 35 * p * effect.strength)
                    * math.sqrt(max(camera.zoom, .2))
                ),
            )
            if effect.kind == "shock":
                color = (235, 100, 95, fade)
            elif effect.kind == "absorb":
                color = (215, 195, 145, fade)
            elif effect.kind == "collapse":
                color = (160, 160, 170, fade)
            elif effect.kind == "emerge":
                color = (115, 220, 205, fade)
            elif effect.kind == "recover":
                color = (105, 220, 160, fade)
            else:
                color = (175, 195, 210, fade // 2)
            self.pg.draw.circle(
                overlay,
                color,
                (round(sx), round(sy)),
                radius,
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
                f"remnants {len(scene.remnants)} · LOD {camera.lod}"
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
