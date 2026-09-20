"""Passive low-cost in-world HUD for the PyBullet embodiment viewer."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from symbiont.core.symbiont import Symbiont

from .runtime import Tick3D


class Physics3DHud:
    """Very low-overhead evaluator HUD using only two debug text items."""

    def __init__(
        self,
        pybullet_module,
        client_id: int,
        *,
        update_every: int = 96,
    ) -> None:
        if update_every < 1:
            raise ValueError("update_every must be >= 1")
        self.p = pybullet_module
        self.client_id = client_id
        self.update_every = update_every
        self._text_id = -1
        self._motor_text_id = -1

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
        limit: int = 4,
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

    def update(
        self,
        record: Tick3D,
        symbiont: Symbiont,
        *,
        last_checkpoint_tick: int,
        embodiment_mode: str,
        symbiont_file: Path,
    ) -> None:
        if record.tick % self.update_every != 0:
            return

        x, y, z = record.base_position
        panel_x = x + 0.72
        panel_y = y + 0.28
        panel_z = max(1.05, z + 0.92)

        checkpoint_age = max(0, record.tick - last_checkpoint_tick)
        summary = (
            f"SYMBIONT 3D  {symbiont.symbiont_id}\n"
            f"tick {record.tick:,}  {embodiment_mode}\n"
            f"schema {record.schema_confidence:0.3f}  "
            f"error {record.prediction_error:0.3f}\n"
            f"outputs {record.active_effectors:02d}  "
            f"motion {record.joint_motion:0.2f}  "
            f"contacts {record.contact_count}\n"
            f"height {record.base_position[2]:+0.3f}m  "
            f"save -{checkpoint_age:,}\n"
            f"{self._safe_text(symbiont_file)}"
        )
        self._text_id = self._replace_text(
            self._text_id,
            summary,
            (panel_x, panel_y, panel_z),
            color=(0.90, 0.96, 1.0),
            size=0.95,
        )

        strongest = self._strongest_outputs(symbiont.last_activations)
        motor_lines = ["OUTPUTS"]
        if strongest:
            motor_lines.extend(
                f"{channel} {value:0.2f}"
                for channel, value in strongest
            )
        else:
            motor_lines.append("(none)")
        self._motor_text_id = self._replace_text(
            self._motor_text_id,
            "\n".join(motor_lines),
            (panel_x, panel_y, panel_z - 0.48),
            color=(0.62, 0.90, 0.88),
            size=0.78,
        )

    def close(self) -> None:
        for item_id in (self._text_id, self._motor_text_id):
            if item_id >= 0:
                try:
                    self.p.removeUserDebugItem(
                        item_id,
                        physicsClientId=self.client_id,
                    )
                except Exception:
                    pass


__all__ = ["Physics3DHud"]
