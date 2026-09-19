from symbiont_lab.viewer.world_pygame import VisualCell, VisualOrganism, project_snapshot


def test_projection_uses_physical_values_without_resource_labels():
    snapshot = {
        "cells": {
            "0,0": {
                "q": 0,
                "r": 0,
                "elevation": 0.7,
                "moisture": 0.4,
                "temperature": 0.3,
                "fertility": 0.8,
                "traces": 0.2,
                "disturbance": 0.1,
                "resources": {"opaque-a": 5.0, "opaque-b": 1.0},
                "resource_capacities": {"opaque-a": 10.0, "opaque-b": 2.0},
                "hazards": {"opaque-h": 0.25},
            }
        },
        "organisms": [
            {
                "id": "founder-0",
                "q": 0,
                "r": 0,
                "alive": True,
                "integrity": 0.9,
                "metabolic_reserve": 0.6,
                "senses_count": 5,
            }
        ],
    }

    cells, organisms = project_snapshot(snapshot)

    assert cells == [
        VisualCell(
            q=0,
            r=0,
            elevation=0.7,
            moisture=0.4,
            temperature=0.3,
            fertility=0.8,
            traces=0.2,
            disturbance=0.1,
            resource_level=0.5,
            hazard_level=0.25,
        )
    ]
    assert organisms == [
        VisualOrganism(
            organism_id="founder-0",
            q=0,
            r=0,
            alive=True,
            integrity=0.9,
            reserve=0.6,
            senses_count=5,
        )
    ]


def test_projection_clamps_non_finite_and_out_of_range_values():
    cells, organisms = project_snapshot(
        {
            "cells": {
                "1,2": {
                    "q": 1,
                    "r": 2,
                    "elevation": 9,
                    "moisture": -3,
                    "temperature": "nan",
                    "fertility": None,
                    "traces": 2,
                    "disturbance": -1,
                    "resources": {},
                    "resource_capacities": {},
                    "hazards": {"h": 4},
                }
            },
            "organisms": [],
        }
    )

    assert organisms == []
    cell = cells[0]
    assert cell.elevation == 1.0
    assert cell.moisture == 0.0
    assert cell.temperature == 0.5
    assert cell.fertility == 0.5
    assert cell.traces == 1.0
    assert cell.disturbance == 0.0
    assert cell.hazard_level == 1.0


def test_viewer_module_has_no_world_runtime_dependency():
    import symbiont_lab.viewer.world_pygame as viewer

    source_names = set(viewer.__dict__)
    assert "WorldRuntimeState" not in source_names
    assert "WorldAction" not in source_names
