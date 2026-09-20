"""Passive in-world HUD for the lightweight PyBullet embodiment viewer."""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Mapping

from symbiont.core.symbiont import Symbiont

from .runtime import Tick3D


class Physics3DHud:
    """Low-overhead evaluator HUD rendered with PyBullet debug primitives."""

    def __init__(
        self,
        pybullet_module,
        client_id: int,
        *,
        history: int = 40,
        update_every: int = 24,
    ) -> None:
        if history < 8:
            raise ValueError("history must be >= 8")
        if update_every < 1:
            raise ValueError("update_every must be >= 1")
        self.p = pybullet_module
        self.client_id = client_id
        self.update_every = update_every
        self.prediction_history: deque[float] = deque(maxlen=history)
        self.schema_history: deque[float] = deque(maxlen=history)
        self._text_id = -1
        self._motor_text_id = -1
        self._prediction_line_ids: list[int] = []
        self._schema_line_ids: list[int] = []

    @staticmethod
    def _safe_text(path: Path, *, max_len: int = 54) -> str:
        text = str(path)
        if len(text) <= max_len:
            return text
        return "..." + text[-(max_len - 3):]

    @staticmethod
    def _strongest_outputs(
        activations: Mapping[str, float],
        *,
        limit: int = 8,
    ) -> list[tuple[str, float]]:
        return sorted(
            ((str(channel), float(value)) for channel, value in activations.items()),
            key=lambda item: (-abs(item[1]), item[0]),
        )[:limit]

    def _replace_text(
        self,
        current_id: int,
        text: str,
        position: tuple[float, float, float],
        *,
        color: tuple[float, float, float],
        size: float,
    ) -> int:
        return int(
            self.p.addUserDebugText(
                text,
                position,
                textColorRGB=color,
                textSize=size,
                replaceItemUniqueId=current_id,
                physicsClientId=self.client_id,
            )
        )

    def _draw_series(
        self,
        values: deque[float],
        line_ids: list[int],
        *,
        origin: tuple[float, float, float],
        width: float,
        height: float,
        clamp_max: float,
        color: tuple[float, float, float],
    ) -> list[int]:
        if len(values) < 2:
            return line_ids

        points = list(values)
        count = len(points)
        segments = count - 1
        while len(line_ids) < segments:
            line_ids.append(-1)

        ox, oy, oz = origin
        denom = max(float(clamp_max), 1e-9)
        for index in range(segments):
            x1 = ox + width * (index / max(1, count - 1))
            x2 = ox + width * ((index + 1) / max(1, count - 1))
            v1 = max(0.0, min(1.0, points[index] / denom))
            v2 = max(0.0, min(1.0, points[index + 1] / denom))
            p1 = (x1, oy, oz + height * v1)
            p2 = (x2, oy, oz + height * v2)
            line_ids[index] = int(
                self.p.addUserDebugLine(
                    p1,
                    p2,
                    lineColorRGB=color,
                    lineWidth=2.0,
                    replaceItemUniqueId=line_ids[index],
                    physicsClientId=self.client_id,
                )
            )

        # Hide stale segments after deque warm-up/resize without removing every frame.
        for index in range(segments, len(line_ids)):
            if line_ids[index] >= 0:
                self.p.removeUserDebugItem(
                    line_ids[index],
                    physicsClientId=self.client_id,
                )
                line_ids[index] = -1
        return line_ids

    def update(
        self,
        record: Tick3D,
        symbiont: Symbiont,
        *,
        last_checkpoint_tick: int,
        embodiment_mode: str,
        symbiont_file: Path,
    ) -> None:
        self.prediction_history.append(record.prediction_error)
        self.schema_history.append(record.schema_confidence)

        if record.tick % self.update_every != 0:
            return

        x, y, z = record.base_position
        panel_x = x + 0.72
        panel_y = y + 0.28
        panel_z = max(1.05, z + 0.92)

        checkpoint_age = max(0, record.tick - last_checkpoint_tick)
        summary = (
            f"SYMBIONT 3D  {symbiont.symbiont_id}\n"
            f"tick {record.tick:,}   mode {embodiment_mode}\n"
            f"body-schema {record.schema_confidence:0.3f}   "
            f"pred-error {record.prediction_error:0.3f}\n"
            f"active-out {record.active_effectors:02d}   "
            f"joint-motion {record.joint_motion:0.2f}   contacts {record.contact_count}\n"
            f"height {record.base_position[2]:+0.3f} m   "
            f"checkpoint -{checkpoint_age:,} ticks\n"
            f"{self._safe_text(symbiont_file)}"
        )
        self._text_id = self._replace_text(
            self._text_id,
            summary,
            (panel_x, panel_y, panel_z),
            color=(0.90, 0.96, 1.0),
            size=1.05,
        )

        strongest = self._strongest_outputs(symbiont.last_activations)
        motor_lines = ["OPAQUE OUTPUT ACTIVITY"]
        if strongest:
            motor_lines.extend(
                f"{channel:<7} {value:0.3f}"
                for channel, value in strongest
            )
        else:
            motor_lines.append("(no outputs yet)")
        self._motor_text_id = self._replace_text(
            self._motor_text_id,
            "\n".join(motor_lines),
            (panel_x, panel_y, panel_z - 0.55),
            color=(0.62, 0.90, 0.88),
            size=0.86,
        )

        graph_y = panel_y + 0.03
        graph_x = panel_x
        graph_z = panel_z - 1.15
        self._prediction_line_ids = self._draw_series(
            self.prediction_history,
            self._prediction_line_ids,
            origin=(graph_x, graph_y, graph_z),
            width=0.95,
            height=0.25,
            clamp_max=1.0,
            color=(0.95, 0.52, 0.36),
        )
        self._schema_line_ids = self._draw_series(
            self.schema_history,
            self._schema_line_ids,
            origin=(graph_x, graph_y + 0.01, graph_z - 0.34),
            width=0.95,
            height=0.25,
            clamp_max=1.0,
            color=(0.42, 0.90, 0.60),
        )

        self.p.addUserDebugText(
            "prediction error",
            (graph_x, graph_y, graph_z + 0.28),
            textColorRGB=(0.95, 0.62, 0.48),
            textSize=0.72,
            lifeTime=0.25,
            physicsClientId=self.client_id,
        )
        self.p.addUserDebugText(
            "body-schema confidence",
            (graph_x, graph_y, graph_z - 0.06),
            textColorRGB=(0.52, 0.95, 0.66),
            textSize=0.72,
            lifeTime=0.25,
            physicsClientId=self.client_id,
        )

    def close(self) -> None:
        for item_id in (
            self._text_id,
            self._motor_text_id,
            *self._prediction_line_ids,
            *self._schema_line_ids,
        ):
            if item_id >= 0:
                try:
                    self.p.removeUserDebugItem(
                        item_id,
                        physicsClientId=self.client_id,
                    )
                except Exception:
                    pass


__all__ = ["Physics3DHud"]
