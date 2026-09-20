"""Passive Pygame habitat for the persistent Symbiont World.

This process consumes Observatory over loopback HTTP. It has no import path to the
World runtime and no ability to pause, step or mutate simulation state.
"""
from __future__ import annotations

import argparse
import time
from urllib.error import HTTPError, URLError

from .camera import Camera, axial_to_world
from .client import WorldObserverClient, validate_loopback_url
from .projection import VisualCell, VisualOrganism, project_snapshot
from .renderer import HabitatRenderer
from .scene import HabitatScene


DEFAULT_STATE_URL = "http://127.0.0.1:8766/world/state"

# Compatibility re-exports retained for callers/tests from the first viewer.
_validate_loopback_url = validate_loopback_url


def _world_extents(scene: HabitatScene) -> tuple[float, float, float, float] | None:
    snapshot = scene.snapshot
    if snapshot is None or not snapshot.cells:
        return None
    points = [axial_to_world(cell.q, cell.r, scene.spacing) for cell in snapshot.cells]
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return min(xs), max(xs), min(ys), max(ys)


def _fit_camera(scene: HabitatScene, camera: Camera, width: int, height: int) -> None:
    extents = _world_extents(scene)
    if extents is None:
        camera.center_on(0.0, 0.0)
        return
    xmin, xmax, ymin, ymax = extents
    camera.center_on((xmin + xmax) / 2.0, (ymin + ymax) / 2.0)
    world_width = max(scene.spacing * 2.0, xmax - xmin + scene.spacing * 2.4)
    world_height = max(scene.spacing * 2.0, ymax - ymin + scene.spacing * 2.4)
    fit = min(width / world_width, height / world_height) * 0.88
    camera.zoom = max(camera.min_zoom, min(camera.max_zoom, fit))


def run(url: str = DEFAULT_STATE_URL, *, fps: int = 60, poll_hz: float = 8.0) -> int:
    try:
        import pygame
    except ImportError as exc:
        raise SystemExit(
            "Pygame viewer is optional. Install with: pip install 'symbiont-lab[viewer]'"
        ) from exc

    client = WorldObserverClient(url)
    pygame.init()
    screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    pygame.display.set_caption("Symbiont World — Voxel Habitat")
    clock = pygame.time.Clock()

    camera = Camera()
    scene = HabitatScene()
    renderer = HabitatRenderer(pygame)

    running = True
    visual_frozen = False
    show_hud = True
    selected_id: str | None = None
    last_state_poll = 0.0
    initialized_camera = False
    error: str | None = None

    while running:
        frame_seconds = max(1.0 / max(fps, 15), clock.get_time() / 1000.0)
        now = time.monotonic()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    visual_frozen = not visual_frozen
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    camera.zoom_by(1.14)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    camera.zoom_by(1 / 1.14)
                elif event.key == pygame.K_h:
                    show_hud = not show_hud
                elif event.key == pygame.K_g:
                    renderer.debug_grid = not renderer.debug_grid
                elif event.key == pygame.K_r:
                    _fit_camera(scene, camera, *screen.get_size())
                    selected_id = None
                elif event.key in (pygame.K_f, pygame.K_TAB):
                    ids = sorted(scene.tracks)
                    if ids:
                        selected_id = ids[0] if selected_id not in ids else ids[(ids.index(selected_id) + 1) % len(ids)]
            elif event.type == pygame.MOUSEWHEEL:
                camera.zoom_by(1.10 ** event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Selection changes only camera/UI state. It never feeds World.
                width, height = screen.get_size()
                best: tuple[float, str] | None = None
                for organism, wx, wy, _ in scene.organism_positions(now):
                    sx, sy = camera.world_to_screen(wx, wy, width, height)
                    distance = ((sx - event.pos[0]) ** 2 + (sy - event.pos[1]) ** 2) ** 0.5
                    if distance <= 22 and (best is None or distance < best[0]):
                        best = (distance, organism.organism_id)
                if best is not None:
                    selected_id = best[1]

        keys = pygame.key.get_pressed()
        pan_speed = 420.0 * frame_seconds
        manual_pan = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            camera.pan_pixels(pan_speed, 0); manual_pan = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            camera.pan_pixels(-pan_speed, 0); manual_pan = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            camera.pan_pixels(0, pan_speed); manual_pan = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            camera.pan_pixels(0, -pan_speed); manual_pan = True
        if manual_pan:
            selected_id = None

        if not visual_frozen and now - last_state_poll >= 1.0 / max(poll_hz, 0.25):
            last_state_poll = now
            try:
                raw = client.fetch_state()
                snapshot = project_snapshot(raw)
                scene.ingest_snapshot(snapshot, now)
                try:
                    scene.ingest_events(client.fetch_events(limit=256), now)
                except (HTTPError, URLError, OSError, ValueError, RuntimeError):
                    # State remains useful if the incremental event feed is
                    # temporarily unavailable.
                    pass
                if not initialized_camera:
                    _fit_camera(scene, camera, *screen.get_size())
                    initialized_camera = True
                error = None
            except (HTTPError, URLError, OSError, ValueError, RuntimeError) as exc:
                error = str(exc)

        scene.update(now)

        if selected_id is not None:
            track = scene.tracks.get(selected_id)
            if track is None:
                selected_id = None
            elif not manual_pan:
                camera.center_on(*track.position(now, scene.transition_seconds))

        renderer.draw(
            screen,
            scene,
            camera,
            now,
            show_hud=show_hud,
            frozen=visual_frozen,
            error=error,
            selected_id=selected_id,
        )
        pygame.display.flip()
        clock.tick(max(15, fps))

    pygame.quit()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Passive voxel/isometric Pygame habitat for Symbiont World")
    parser.add_argument("--url", default=DEFAULT_STATE_URL, help="local Observatory /world/state URL")
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--poll-hz", type=float, default=8.0)
    args = parser.parse_args(argv)
    return run(args.url, fps=args.fps, poll_hz=args.poll_hz)


if __name__ == "__main__":
    raise SystemExit(main())
