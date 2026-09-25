"""Observer-only semantic labels for the Physics3D apparatus.

These labels are evaluator ground truth. They are never exposed to the
organism's discovery, sensory, cognition, BodySchema, or actuation inputs.
"""

from __future__ import annotations

from collections.abc import Iterable

_INTEROCEPTIVE_SOURCE_LABELS = (
    "energy reserve",
    "structural integrity",
    "temperature",
    "fatigue",
)


def _humanize(token: str) -> str:
    return token.replace("_", " ")


def receptor_ground_truth(
    *,
    joint_specs: Iterable[object],
    contact_region_names: tuple[str, ...],
    interoceptive_source_ordinals: tuple[int, ...],
) -> dict[str, dict[str, str]]:
    """Return exact evaluator meaning for every canonical opaque receptor."""
    labels: dict[str, dict[str, str]] = {}
    ordinal = 0

    for spec in joint_specs:
        joint = _humanize(spec.name)
        labels[f"rec.{ordinal}"] = {
            "label": f"{joint} angle",
            "category": "proprioception",
        }
        ordinal += 1
        labels[f"rec.{ordinal}"] = {
            "label": f"{joint} angular velocity",
            "category": "proprioception",
        }
        ordinal += 1

    for component in ("x", "y", "z", "w"):
        labels[f"rec.{ordinal}"] = {
            "label": f"base orientation {component}",
            "category": "kinematics",
        }
        ordinal += 1

    for component in ("x", "y", "z"):
        labels[f"rec.{ordinal}"] = {
            "label": f"base linear velocity {component}",
            "category": "kinematics",
        }
        ordinal += 1

    for component in ("x", "y", "z"):
        labels[f"rec.{ordinal}"] = {
            "label": f"base angular velocity {component}",
            "category": "kinematics",
        }
        ordinal += 1

    for region in contact_region_names:
        labels[f"rec.{ordinal}"] = {
            "label": f"{_humanize(region)} contact",
            "category": "contact",
        }
        ordinal += 1

    labels[f"rec.{ordinal}"] = {
        "label": "resource field intensity",
        "category": "environment",
    }
    ordinal += 1

    for region in contact_region_names:
        labels[f"rec.{ordinal}"] = {
            "label": f"{_humanize(region)} contact load",
            "category": "contact",
        }
        ordinal += 1

    for source_ordinal in interoceptive_source_ordinals:
        if not 0 <= source_ordinal < len(_INTEROCEPTIVE_SOURCE_LABELS):
            raise ValueError("invalid interoceptive source ordinal")
        labels[f"rec.{ordinal}"] = {
            "label": _INTEROCEPTIVE_SOURCE_LABELS[source_ordinal],
            "category": "interoception",
        }
        ordinal += 1

    return labels


def sensory_semantics(
    sensors: Iterable[object],
    *,
    joint_specs: Iterable[object],
    contact_region_names: tuple[str, ...],
    interoceptive_source_ordinals: tuple[int, ...],
) -> dict[str, dict[str, object]]:
    """Map organism-owned cognitive sensor names to apparatus ground truth."""
    truth = receptor_ground_truth(
        joint_specs=joint_specs,
        contact_region_names=contact_region_names,
        interoceptive_source_ordinals=interoceptive_source_ordinals,
    )
    result: dict[str, dict[str, object]] = {}

    for sensor in sensors:
        self_label = str(getattr(sensor, "cognitive_name", "") or "")
        if not self_label:
            continue
        source_ids = tuple(str(item) for item in tuple(getattr(sensor, "source_ids", ()) or ()))
        matches = [truth[source_id] for source_id in source_ids if source_id in truth]
        observer_labels = [str(item["label"]) for item in matches]
        categories = sorted({str(item["category"]) for item in matches})

        result[self_label] = {
            "self_label": self_label,
            "source_ids": list(source_ids),
            "observer_labels": observer_labels,
            "observer_summary": (
                observer_labels[0]
                if len(observer_labels) == 1
                else " + ".join(observer_labels[:3])
                if observer_labels
                else None
            ),
            "observer_categories": categories,
            "mapping": (
                "exact-source"
                if len(source_ids) == 1 and len(observer_labels) == 1
                else "composite-source"
                if observer_labels
                else "unresolved"
            ),
        }

    return result


def motor_semantics(
    actuator_to_effector: dict[str, str],
    *,
    joint_specs: tuple[object, ...],
) -> dict[str, dict[str, str]]:
    """Map opaque organism actuator ids to evaluator-only physical meaning."""
    result: dict[str, dict[str, str]] = {}
    for actuator_id, effector_id in sorted(actuator_to_effector.items()):
        try:
            ordinal = int(str(effector_id).split(".", 1)[1])
        except (IndexError, ValueError):
            continue
        joint_ordinal = ordinal // 2
        if not 0 <= joint_ordinal < len(joint_specs):
            continue
        direction = "positive" if ordinal % 2 == 0 else "negative"
        joint = _humanize(str(getattr(joint_specs[joint_ordinal], "name")))
        result[str(actuator_id)] = {
            "self_label": str(actuator_id),
            "effector_id": str(effector_id),
            "observer_summary": f"{joint} {direction} drive",
            "joint": joint,
            "direction": direction,
        }
    return result


__all__ = ["motor_semantics", "receptor_ground_truth", "sensory_semantics"]
