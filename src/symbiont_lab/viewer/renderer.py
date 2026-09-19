"""Pygame habitat renderer.

The renderer consumes only projected observer state. It never imports World.
"""
from __future__ import annotations

import math

from .camera import Camera, axial_to_world
from .projection import VisualCell, VisualOrganism
from .scene import HabitatScene, Morphology, VisualEffect


def cell_rgb(cell: VisualCell) -> tuple[int, int, int]:
    altitude = cell.elevation
    wet = cell.moisture
    fertile = cell.fertility
    heat = cell.temperature
    hazard = cell.hazard_level
    disturbance = cell.disturbance
    r = 24 + int(60 * heat) + int(50 * hazard) + int(25 * disturbance)
    g = 32 + int(105 * fertile) + int(34 * wet) - int(38 * hazard)
    b = 38 + int(92 * wet) - int(24 * heat) + int(15 * altitude)
    shade = 0.7 + 0.3 * altitude
    return tuple(max(0, min(255, int(channel * shade))) for channel in (r, g, b))


def _hex_points(cx: float, cy: float, radius: float) -> list[tuple[int, int]]:
    return [
        (
            round(cx + radius * math.cos(math.radians(60 * i - 30))),
            round(cy + radius * math.sin(math.radians(60 * i - 30))),
        )
        for i in range(6)
    ]


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
        screen.fill((5, 9, 14))
        visible_count = 0

        snapshot = scene.snapshot
        if snapshot is not None:
            bounds = camera.axial_bounds(width, height, scene.spacing)
            cells = scene.visible_cells(bounds)
            organism_ids = scene.visible_track_ids(bounds)
            self._draw_terrain(screen, scene, camera, cells)
            self._draw_environment(screen, scene, camera, cells)
            visible_count = self._draw_organisms(screen, scene, camera, now, selected_id, organism_ids)
            self._draw_effects(screen, scene.effects, camera, now)

        if show_hud:
            self._draw_hud(screen, scene, camera, visible_count, frozen, error, selected_id)
        return visible_count

    def _draw_terrain(self, screen, scene: HabitatScene, camera: Camera, cells: list[VisualCell]) -> None:
        width, height = screen.get_size()
        world_radius = scene.spacing * 1.06
        radius = world_radius * camera.zoom

        # Overlapping borderless cells + translucent soft overlays hide the
        # computational grid while preserving the physical field underneath.
        haze = self.pg.Surface((width, height), self.pg.SRCALPHA)
        for cell in cells:
            wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
            if not camera.visible(wx, wy, width, height, margin=radius * 2):
                continue
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            color = cell_rgb(cell)
            self.pg.draw.polygon(screen, color, _hex_points(sx, sy, radius + 1.5))
            if camera.lod != "far":
                soft = (
                    min(255, color[0] + 12),
                    min(255, color[1] + 12),
                    min(255, color[2] + 12),
                    22,
                )
                self.pg.draw.circle(haze, soft, (round(sx), round(sy)), max(2, round(radius * 0.82)))
            if self.debug_grid:
                self.pg.draw.polygon(screen, (65, 82, 95), _hex_points(sx, sy, radius), 1)
        screen.blit(haze, (0, 0))

    def _draw_environment(self, screen, scene: HabitatScene, camera: Camera, cells: list[VisualCell]) -> None:
        width, height = screen.get_size()
        if camera.lod == "far":
            return
        overlay = self.pg.Surface((width, height), self.pg.SRCALPHA)
        cell_map = {(cell.q, cell.r): cell for cell in cells}
        # Connect neighboring high-trace cells so repeated traffic becomes
        # a visible path rather than disconnected telemetry markers.
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
                    (175, 165, 148, 20 + int(90 * strength)),
                    (round(asx), round(asy)),
                    (round(bsx), round(bsy)),
                    max(1, round((1.0 + 2.5 * strength) * camera.zoom)),
                )
        for cell in cells:
            wx, wy = axial_to_world(cell.q, cell.r, scene.spacing)
            if not camera.visible(wx, wy, width, height, margin=80):
                continue
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            z = camera.zoom
            if cell.resource_level > 0.03:
                # Multiple small bodies read as material abundance, not a named resource.
                count = min(7, 1 + int(cell.resource_level * 7))
                for i in range(count):
                    angle = (i * 2.399963 + (cell.q * 0.7 + cell.r * 1.1)) % math.tau
                    distance = (8 + (i % 3) * 6) * z
                    px = round(sx + math.cos(angle) * distance)
                    py = round(sy + math.sin(angle) * distance)
                    size = max(1, round((2.0 + 2.8 * cell.resource_level) * math.sqrt(z)))
                    self.pg.draw.circle(overlay, (205, 190, 150, 150), (px, py), size)
            if cell.hazard_level > 0.025:
                rr = max(5, round(scene.spacing * z * (0.28 + 0.5 * cell.hazard_level)))
                self.pg.draw.circle(overlay, (210, 80, 78, 22 + int(55 * cell.hazard_level)), (round(sx), round(sy)), rr)
            if cell.traces > 0.025:
                count = min(8, 1 + int(cell.traces * 8))
                for i in range(count):
                    offset = (i - (count - 1) / 2) * 4.0 * z
                    self.pg.draw.circle(
                        overlay,
                        (185, 175, 155, 24 + int(80 * cell.traces)),
                        (round(sx + offset), round(sy + offset * 0.25)),
                        max(1, round(1.5 * z)),
                    )
            if cell.disturbance > 0.04:
                rr = max(3, round(scene.spacing * z * (0.15 + cell.disturbance * 0.35)))
                self.pg.draw.circle(overlay, (230, 190, 130, 40), (round(sx), round(sy)), rr, max(1, round(z)))
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
                color = (108, 210, 213) if organism.alive else (85, 88, 92)
                self.pg.draw.circle(screen, color, (round(sx), round(sy)), 2 if camera.zoom < .3 else 3)
            return len(visible)

        for organism, wx, wy, morphology in visible:
            sx, sy = camera.world_to_screen(wx, wy, width, height)
            track = scene.tracks.get(organism.organism_id)
            if track is not None and track.previous != track.target and camera.lod == "near":
                psx, psy = camera.world_to_screen(track.previous[0], track.previous[1], width, height)
                self.pg.draw.line(
                    screen,
                    (92, 145, 155),
                    (round(psx), round(psy)),
                    (round(sx), round(sy)),
                    max(1, round(camera.zoom)),
                )
            self._draw_organism(screen, organism, morphology, sx, sy, camera.zoom, now, selected_id == organism.organism_id)
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
        selected: bool,
    ) -> None:
        integrity = 0.5 if organism.integrity is None else organism.integrity
        reserve = 0.5 if organism.reserve is None else organism.reserve
        pulse = 1.0 + math.sin(now * 2.0 + morphology.pulse_phase) * 0.035
        base = max(4.0, (7.0 + 7.5 * reserve) * math.sqrt(max(zoom, .25)) * morphology.core_scale * pulse)
        if not organism.alive:
            base *= 0.84

        # Phenotype-derived radial body: sensors/generation affect visible morphology,
        # while color/size reflect current condition.
        points: list[tuple[int, int]] = []
        lobes = morphology.lobes
        for i in range(lobes * 2):
            angle = morphology.symmetry_offset + i * math.pi / lobes
            radius = base * (1.0 if i % 2 == 0 else 0.72)
            points.append((round(sx + math.cos(angle) * radius), round(sy + math.sin(angle) * radius)))

        color = (
            78 + int(80 * reserve),
            130 + int(105 * integrity),
            178 + int(45 * reserve),
        ) if organism.alive else (82, 86, 90)
        self.pg.draw.polygon(screen, color, points)
        self.pg.draw.circle(screen, (215, 235, 238), (round(sx), round(sy)), max(2, round(base * .35)), 1)

        if zoom >= 0.65:
            arms = min(organism.senses_count, 16)
            for arm in range(arms):
                angle = morphology.symmetry_offset + math.tau * arm / max(arms, 1)
                length = base * (1.25 + 0.35 * morphology.appendage_scale)
                end = (round(sx + math.cos(angle) * length), round(sy + math.sin(angle) * length))
                self.pg.draw.line(screen, (115, 196, 208), (round(sx), round(sy)), end, 1)

        if organism.recent_damage > 0:
            self.pg.draw.circle(screen, (235, 110, 105), (round(sx), round(sy)), round(base * 1.25), 1)
        if selected:
            self.pg.draw.circle(screen, (242, 207, 105), (round(sx), round(sy)), round(base + 8), 2)

    def _draw_effects(self, screen, effects: list[VisualEffect], camera: Camera, now: float) -> None:
        width, height = screen.get_size()
        overlay = self.pg.Surface((width, height), self.pg.SRCALPHA)
        for effect in effects:
            if not camera.visible(effect.x, effect.y, width, height, margin=100):
                continue
            sx, sy = camera.world_to_screen(effect.x, effect.y, width, height)
            p = effect.progress(now)
            fade = max(0, int(180 * (1.0 - p)))
            radius = max(3, round((8 + 35 * p * effect.strength) * math.sqrt(max(camera.zoom, .2))))
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
            self.pg.draw.circle(overlay, color, (round(sx), round(sy)), radius, max(1, round(2 * camera.zoom)))
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
            f"World · tick {tick} · visible {visible_count}/{total} · LOD {camera.lod}",
            "WASD/arrows pan   +/- zoom   F/TAB follow   R fit world   G grid   H HUD   SPACE freeze   ESC quit",
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
