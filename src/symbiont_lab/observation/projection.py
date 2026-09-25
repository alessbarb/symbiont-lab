"""Pure observer-side projections from runtime telemetry into view contracts."""
from __future__ import annotations

from typing import Any, Mapping


def _identity(tick: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if tick.get("source") is not None:
        result["source"] = str(tick["source"])
    if tick.get("instance_id") is not None:
        result["instance_id"] = str(tick["instance_id"])
    if tick.get("run_id") is not None:
        result["run_id"] = str(tick["run_id"])
    if tick.get("sequence") is not None:
        try:
            result["sequence"] = int(tick["sequence"])
        except (TypeError, ValueError):
            pass
    return result


def _copy_number(
    target: dict[str, Any],
    source: Mapping[str, Any],
    source_key: str,
    *,
    target_key: str | None = None,
    cast: type[int] | type[float] = float,
) -> None:
    value = source.get(source_key)
    if value is None:
        return
    try:
        target[target_key or source_key] = cast(value)
    except (TypeError, ValueError):
        return


def _copy_bool(
    target: dict[str, Any],
    source: Mapping[str, Any],
    source_key: str,
    *,
    target_key: str | None = None,
) -> None:
    value = source.get(source_key)
    if isinstance(value, bool):
        target[target_key or source_key] = value


def runtime_tick_events(tick: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Project one canonical runtime tick without fabricating absent observations."""
    if not isinstance(tick, Mapping):
        raise TypeError("tick must be a mapping")

    identity = _identity(tick)

    body: dict[str, Any] = {**identity, "type": "body"}
    _copy_number(body, tick, "tick", cast=int)
    if tick.get("body_kind") is not None:
        body["body_kind"] = str(tick["body_kind"])
    if isinstance(tick.get("base_position"), (list, tuple)):
        try:
            body["base_position"] = [float(v) for v in tick["base_position"]]
        except (TypeError, ValueError):
            pass
    if isinstance(tick.get("base_orientation"), (list, tuple)):
        try:
            body["base_orientation"] = [float(v) for v in tick["base_orientation"]]
        except (TypeError, ValueError):
            pass
    if isinstance(tick.get("resource_position"), (list, tuple)):
        try:
            position = [float(v) for v in tick["resource_position"]]
            if len(position) == 3:
                body["resource_position"] = position
        except (TypeError, ValueError):
            pass
    if isinstance(tick.get("joints"), (list, tuple)):
        joints: list[dict[str, Any]] = []
        for item in tick["joints"]:
            if not isinstance(item, Mapping):
                continue
            joint: dict[str, Any] = {}
            if item.get("name") is not None:
                joint["name"] = str(item["name"])
            if item.get("position") is not None:
                try:
                    joint["position"] = float(item["position"])
                except (TypeError, ValueError):
                    pass
            if joint:
                joints.append(joint)
        body["joints"] = joints
    if isinstance(tick.get("links"), (list, tuple)):
        links: list[dict[str, Any]] = []
        for item in tick["links"]:
            if not isinstance(item, Mapping) or item.get("name") is None:
                continue
            raw_position = item.get("position")
            raw_orientation = item.get("orientation")
            if (
                not isinstance(raw_position, (list, tuple))
                or len(raw_position) != 3
                or not isinstance(raw_orientation, (list, tuple))
                or len(raw_orientation) != 4
            ):
                continue
            try:
                links.append(
                    {
                        "name": str(item["name"]),
                        "position": [float(v) for v in raw_position],
                        "orientation": [float(v) for v in raw_orientation],
                    }
                )
            except (TypeError, ValueError):
                continue
        if links:
            body["links"] = links
    _copy_number(body, tick, "contact_count", cast=int)
    _copy_number(body, tick, "ground_contact_count", cast=int)
    _copy_number(body, tick, "self_contact_count", cast=int)
    _copy_number(body, tick, "resource_contact_count", cast=int)
    if tick.get("metabolic_reserve_ratio") is not None:
        _copy_number(body, tick, "metabolic_reserve_ratio", target_key="metabolic_reserve")
    elif tick.get("metabolic_reserve") is not None:
        _copy_number(body, tick, "metabolic_reserve")

    cognition: dict[str, Any] = {**identity, "type": "cognition"}
    _copy_number(cognition, tick, "tick", cast=int)
    _copy_number(cognition, tick, "symbiont_tick", cast=int)
    _copy_number(cognition, tick, "schema_confidence")
    _copy_number(cognition, tick, "schema_parts", cast=int)
    _copy_number(cognition, tick, "schema_sensory_parts", cast=int)
    _copy_number(cognition, tick, "schema_cognitive_regions", cast=int)
    _copy_number(cognition, tick, "embodiment_epoch", cast=int)
    _copy_number(cognition, tick, "body_age_ticks", cast=int)
    _copy_number(cognition, tick, "body_senescence")
    _copy_number(cognition, tick, "reacclimation_remaining", cast=int)
    _copy_bool(cognition, tick, "reacclimating")
    if tick.get("motor_origin") is not None:
        cognition["motor_origin"] = str(tick["motor_origin"])
    if tick.get("motor_origin_detail") is not None:
        cognition["motor_origin_detail"] = str(tick["motor_origin_detail"])
    _copy_number(cognition, tick, "predictor_count", cast=int)
    _copy_number(cognition, tick, "sensorimotor_patterns", cast=int)
    _copy_number(cognition, tick, "motor_primitives", cast=int)
    _copy_number(cognition, tick, "cognitive_motor_primitives", cast=int)
    _copy_number(cognition, tick, "motor_repertoire_size", cast=int)
    _copy_number(cognition, tick, "recurrent_primitive_candidates", cast=int)
    _copy_number(cognition, tick, "max_primitive_samples", cast=int)
    _copy_number(cognition, tick, "full_competence_gate_candidates", cast=int)
    _copy_number(cognition, tick, "motor_readout_nodes", cast=int)
    _copy_number(cognition, tick, "primitive_readout_nodes", cast=int)
    _copy_number(cognition, tick, "cognitive_motor_output_edges", cast=int)
    _copy_number(cognition, tick, "cognitive_concepts", cast=int)
    _copy_number(cognition, tick, "cognitive_readouts", cast=int)
    if "prediction_error" in tick:
        cognition["prediction_error"] = tick.get("prediction_error")
    _copy_bool(cognition, tick, "slm_active")
    if "slm_models" in tick:
        cognition["slm_models"] = tick.get("slm_models")
    _copy_bool(cognition, tick, "prospective_selected")
    if "prospective_expected_value" in tick:
        cognition["prospective_expected_value"] = tick.get("prospective_expected_value")

    vitals: dict[str, Any] = {**identity, "type": "vitals"}
    _copy_number(vitals, tick, "tick", cast=int)
    _copy_number(vitals, tick, "symbiont_tick", cast=int)
    _copy_number(vitals, tick, "body_age_ticks", cast=int)
    _copy_number(vitals, tick, "body_senescence")
    _copy_bool(vitals, tick, "alive")
    _copy_number(vitals, tick, "joint_motion")
    _copy_number(vitals, tick, "active_effectors", cast=int)
    _copy_number(vitals, tick, "resource_distance")
    _copy_number(vitals, tick, "resource_progress")
    _copy_number(vitals, tick, "resource_remaining")
    _copy_number(vitals, tick, "displacement_from_origin")
    _copy_number(vitals, tick, "mechanical_work_joules")
    _copy_number(vitals, tick, "positive_actuator_work_joules")
    _copy_number(vitals, tick, "negative_actuator_work_joules")
    _copy_number(vitals, tick, "absolute_actuator_work_joules")
    _copy_number(vitals, tick, "net_actuator_work_joules")
    _copy_number(vitals, tick, "metabolic_work_cost")

    return body, cognition, vitals


def _prediction_class(value: object) -> str | None:
    try:
        error = abs(float(value))
    except (TypeError, ValueError):
        return None
    if error <= 1e-12:
        return "zero"
    if error < 0.01:
        return "trace"
    if error < 0.05:
        return "low"
    if error < 0.15:
        return "medium"
    if error < 0.4:
        return "high"
    return "extreme"


def mind_snapshot_from_rich_state(rich_state: Mapping[str, Any]) -> dict[str, Any]:
    """Translate passive Physics3D telemetry into the Mind view contract."""
    raw_runtime = rich_state.get("runtime")
    runtime_present = isinstance(raw_runtime, Mapping)
    runtime = raw_runtime if runtime_present else {}
    raw_cognition = rich_state.get("cognition")
    cognition_present = isinstance(raw_cognition, Mapping)
    cognition = raw_cognition if cognition_present else {}
    raw_topology = rich_state.get("cognitive_topology")
    topology_present = isinstance(raw_topology, Mapping)
    topology = raw_topology if topology_present else None
    raw_post = rich_state.get("post")
    post_present = isinstance(raw_post, Mapping)
    post = raw_post if post_present else {}

    raw_observer_semantics = rich_state.get("observer_semantics")
    observer_semantics_present = isinstance(raw_observer_semantics, Mapping)
    observer_semantics_source = (
        raw_observer_semantics if observer_semantics_present else {}
    )

    senses: list[dict[str, Any]] = []
    raw_percepts = runtime.get("percepts", ())
    if isinstance(raw_percepts, (list, tuple)):
        for index, item in enumerate(raw_percepts[:64]):
            if not isinstance(item, Mapping):
                continue
            sense_id = str(item.get("name") or item.get("capability_id") or item.get("id") or f"sense.{index}")
            sense: dict[str, Any] = {"id": sense_id, "name": sense_id}
            if item.get("quality") is not None:
                sense["quality"] = item["quality"]
            if isinstance(item.get("available"), bool):
                sense["active"] = item["available"]
            senses.append(sense)

    beliefs: list[dict[str, Any]] = []
    raw_narrative = runtime.get("narrative", ())
    if isinstance(raw_narrative, (list, tuple)):
        for index, item in enumerate(raw_narrative[:64]):
            if not isinstance(item, Mapping):
                continue
            belief_id = str(item.get("capability_id") or item.get("id") or f"belief.{index}")
            belief: dict[str, Any] = {
                "id": belief_id,
                "title": str(item.get("summary") or belief_id),
            }
            uncertainty = item.get("uncertainty")
            if uncertainty is not None:
                try:
                    belief["certainty"] = max(0.0, min(1.0, 1.0 - float(uncertainty)))
                except (TypeError, ValueError):
                    pass
            if item.get("evidence_gathered") is not None:
                try:
                    belief["evidence"] = int(item["evidence_gathered"])
                except (TypeError, ValueError):
                    pass
            if isinstance(item.get("contested"), bool):
                belief["contested"] = item["contested"]
            if "dissent" in item:
                belief["dissent"] = item.get("dissent") is not None
            beliefs.append(belief)

    activation_values: dict[str, float] = {}
    activation_classes: dict[str, int] = {}
    raw_activations = cognition.get("activations")
    if isinstance(raw_activations, Mapping):
        for key, value in raw_activations.items():
            try:
                numeric = float(value)
                activation_values[str(key)] = numeric
                activation_classes[str(key)] = max(
                    0,
                    min(15, int(round(abs(numeric) * 15.0))),
                )
            except (TypeError, ValueError):
                continue

    prediction_errors: dict[str, str] = {}
    prediction_error_values: dict[str, float] = {}
    raw_errors = cognition.get("prediction_errors")
    if isinstance(raw_errors, (list, tuple)):
        for item in raw_errors:
            if not isinstance(item, Mapping):
                continue
            target = str(item.get("target_id") or item.get("predictor_id") or "")
            try:
                numeric_error = float(item.get("error"))
            except (TypeError, ValueError):
                numeric_error = None
            classification = _prediction_class(item.get("error"))
            if target and numeric_error is not None:
                prediction_error_values[target] = numeric_error
            if target and classification is not None:
                prediction_errors[target] = classification

    mind_cognition: dict[str, Any] = {}
    if isinstance(cognition.get("readouts"), Mapping):
        mind_cognition["readouts"] = dict(cognition["readouts"])
    if cognition.get("topology_health") is not None:
        mind_cognition["topologyHealth"] = str(cognition["topology_health"])
    safety_state: dict[str, Any] = {}
    if isinstance(cognition.get("frozen"), bool):
        safety_state["frozen"] = cognition["frozen"]
    if isinstance(cognition.get("recovering"), bool):
        safety_state["recovering"] = cognition["recovering"]
    if cognition.get("consecutive_failures") is not None:
        try:
            safety_state["consecutiveFailures"] = int(cognition["consecutive_failures"])
        except (TypeError, ValueError):
            pass
    if safety_state:
        mind_cognition["safetyState"] = safety_state
    if isinstance(cognition.get("stranded_concepts"), (list, tuple)):
        mind_cognition["strandedConcepts"] = list(cognition["stranded_concepts"])
    if cognition.get("predictive_gain") is not None:
        try:
            mind_cognition["predictiveGain"] = float(cognition["predictive_gain"])
        except (TypeError, ValueError):
            pass
    if isinstance(cognition.get("representation_maturity"), Mapping):
        mind_cognition["representationMaturity"] = dict(cognition["representation_maturity"])
    if cognition.get("topology_revision") is not None:
        try:
            mind_cognition["topologyRevision"] = int(cognition["topology_revision"])
        except (TypeError, ValueError):
            pass

    observer_analysis: dict[str, Any] = {}
    derivation: dict[str, str] = {}
    if activation_values:
        observer_analysis["activationValues"] = activation_values
        derivation["activationValues"] = "observer-preserved numeric activation from cognition telemetry"
    if activation_classes:
        observer_analysis["activationClasses"] = activation_classes
        derivation["activationClasses"] = "observer quantization of absolute activation into 0..15"
    if prediction_error_values:
        observer_analysis["predictionErrorValues"] = prediction_error_values
        derivation["predictionErrorValues"] = "observer-preserved numeric prediction error"
    if prediction_errors:
        observer_analysis["predictionErrors"] = prediction_errors
        derivation["predictionErrors"] = "observer classification of numeric prediction error"
    if derivation:
        observer_analysis["derivation"] = derivation

    mind_topology = None
    if topology is not None:
        nodes = []
        for item in topology.get("nodes", ()) or ():
            if isinstance(item, Mapping):
                node: dict[str, Any] = {}
                if item.get("node_id") is not None or item.get("id") is not None:
                    node["id"] = str(item.get("node_id") or item.get("id"))
                if item.get("kind") is not None:
                    node["kind"] = str(item["kind"])
                if item.get("predicts_node_id") is not None:
                    node["predictsNodeId"] = str(item["predicts_node_id"])
                for source_key, target_key in (("bias", "bias"), ("tau", "tau")):
                    if item.get(source_key) is not None:
                        try:
                            node[target_key] = float(item[source_key])
                        except (TypeError, ValueError):
                            pass
                if node:
                    nodes.append(node)
        edges = []
        for item in topology.get("edges", ()) or ():
            if isinstance(item, Mapping):
                edge: dict[str, Any] = {}
                source = item.get("source_id") if item.get("source_id") is not None else item.get("sourceId")
                target = item.get("target_id") if item.get("target_id") is not None else item.get("targetId")
                if source is not None:
                    edge["sourceId"] = str(source)
                if target is not None:
                    edge["targetId"] = str(target)
                if item.get("kind") is not None:
                    edge["kind"] = str(item["kind"])
                for source_key, target_key, caster in (
                    ("weight", "weight", float),
                    ("plasticity", "plasticity", float),
                    ("delay_ticks", "delayTicks", int),
                    ("support", "support", int),
                    ("age_ticks", "ageTicks", int),
                    ("stable_ticks", "stableTicks", int),
                    ("last_use_tick", "lastUseTick", int),
                ):
                    if item.get(source_key) is not None:
                        try:
                            edge[target_key] = caster(item[source_key])
                        except (TypeError, ValueError):
                            pass
                if edge:
                    edges.append(edge)
        mind_topology = {"nodes": nodes, "edges": edges}

    observer_semantics: dict[str, Any] = {}
    raw_sensory_semantics = observer_semantics_source.get("sensory")
    if isinstance(raw_sensory_semantics, Mapping):
        sensory_semantics: dict[str, dict[str, Any]] = {}
        for key, value in raw_sensory_semantics.items():
            if not isinstance(value, Mapping):
                continue
            entry: dict[str, Any] = {}
            if value.get("self_label") is not None:
                entry["selfLabel"] = str(value["self_label"])
            if isinstance(value.get("source_ids"), (list, tuple)):
                entry["sourceIds"] = [str(item) for item in value["source_ids"][:8]]
            if isinstance(value.get("observer_labels"), (list, tuple)):
                entry["observerLabels"] = [
                    str(item) for item in value["observer_labels"][:8]
                ]
            if value.get("observer_summary") is not None:
                entry["observerSummary"] = str(value["observer_summary"])
            if isinstance(value.get("observer_categories"), (list, tuple)):
                entry["observerCategories"] = [
                    str(item) for item in value["observer_categories"][:8]
                ]
            if value.get("mapping") is not None:
                entry["mapping"] = str(value["mapping"])
            if entry:
                sensory_semantics[str(key)] = entry
        if sensory_semantics:
            observer_semantics["sensory"] = sensory_semantics
    raw_motor_semantics = observer_semantics_source.get("motor")
    if isinstance(raw_motor_semantics, Mapping):
        motor_semantics: dict[str, dict[str, Any]] = {}
        for key, value in raw_motor_semantics.items():
            if not isinstance(value, Mapping):
                continue
            entry = {
                "selfLabel": str(value.get("self_label") or key),
                "effectorId": str(value.get("effector_id") or ""),
                "observerSummary": str(value.get("observer_summary") or ""),
                "joint": str(value.get("joint") or ""),
                "direction": str(value.get("direction") or ""),
            }
            motor_semantics[str(key)] = entry
        if motor_semantics:
            observer_semantics["motor"] = motor_semantics
    raw_semantics_provenance = observer_semantics_source.get("provenance")
    if isinstance(raw_semantics_provenance, Mapping):
        observer_semantics["provenance"] = {
            "owner": str(raw_semantics_provenance.get("owner") or "observer"),
            "source": str(raw_semantics_provenance.get("source") or "unknown"),
            "feedsBack": bool(raw_semantics_provenance.get("feeds_back", False)),
        }

    metabolism = post.get("metabolism")
    if not isinstance(metabolism, Mapping):
        metabolism = None
    development = runtime.get("development")
    if not isinstance(development, Mapping):
        development = None
    sensory_phenotype = runtime.get("sensory_phenotype")
    if not isinstance(sensory_phenotype, Mapping):
        sensory_phenotype = None
    physiology = post.get("physiology")
    if not isinstance(physiology, Mapping):
        physiology = None
    self_model = rich_state.get("self_model")
    if not isinstance(self_model, Mapping):
        self_model = None
    sensorimotor = rich_state.get("sensorimotor")
    if not isinstance(sensorimotor, Mapping):
        sensorimotor = None
    motor_competences = rich_state.get("motor_competences")
    if not isinstance(motor_competences, (list, tuple)):
        motor_competences = None
    effects = rich_state.get("effects")
    if not isinstance(effects, (list, tuple)):
        effects = None
    outcome = rich_state.get("outcome")
    if not isinstance(outcome, Mapping):
        outcome = None

    snapshot: dict[str, Any] = {}
    embodiment_source = rich_state
    if isinstance(runtime, Mapping) and any(
        key in runtime
        for key in ("embodiment_epoch", "reacclimating", "reacclimation_remaining")
    ):
        embodiment_source = runtime
    elif isinstance(cognition, Mapping) and any(
        key in cognition
        for key in ("embodiment_epoch", "reacclimating", "reacclimation_remaining")
    ):
        embodiment_source = cognition
    embodiment: dict[str, Any] = {}
    if embodiment_source.get("embodiment_epoch") is not None:
        try:
            embodiment["epoch"] = int(embodiment_source["embodiment_epoch"])
        except (TypeError, ValueError):
            pass
    if isinstance(embodiment_source.get("reacclimating"), bool):
        embodiment["reacclimating"] = embodiment_source["reacclimating"]
    if embodiment_source.get("reacclimation_remaining") is not None:
        try:
            embodiment["reacclimationRemaining"] = int(
                embodiment_source["reacclimation_remaining"]
            )
        except (TypeError, ValueError):
            pass
    raw_embodiment_block = rich_state.get("embodiment")
    if isinstance(raw_embodiment_block, Mapping):
        raw_bindings = raw_embodiment_block.get("bindings")
        if isinstance(raw_bindings, (list, tuple)):
            embodiment["bindings"] = [
                dict(item) for item in raw_bindings if isinstance(item, Mapping)
            ]
    if embodiment:
        snapshot["embodiment"] = embodiment

    organism_facts: list[str] = []
    observer_derived: list[str] = []

    if embodiment:
        organism_facts.append("embodiment")
    if runtime_present and "percepts" in runtime:
        snapshot["senses"] = senses
        organism_facts.append("senses")
    if runtime_present and "narrative" in runtime:
        snapshot["beliefs"] = beliefs
        organism_facts.append("beliefs")
    if cognition_present:
        snapshot["cognition"] = mind_cognition
        organism_facts.append("cognition")
    if topology_present:
        snapshot["topology"] = mind_topology
        organism_facts.append("topology")
    if self_model is not None:
        snapshot["self_model"] = dict(self_model)
        organism_facts.append("self_model")
    if "body_schema" in rich_state:
        snapshot["body_schema"] = rich_state.get("body_schema")
        organism_facts.append("body_schema")
    if sensory_phenotype is not None:
        snapshot["sensory_phenotype"] = sensory_phenotype
        organism_facts.append("sensory_phenotype")
    if metabolism is not None:
        snapshot["metabolism"] = metabolism
        organism_facts.append("metabolism")
    if development is not None:
        snapshot["development"] = development
        organism_facts.append("development")
    if physiology is not None:
        snapshot["organism_state"] = physiology
        organism_facts.append("organism_state")
    if sensorimotor is not None:
        snapshot["sensorimotor"] = dict(sensorimotor)
        organism_facts.append("sensorimotor")
    if motor_competences is not None:
        snapshot["motor_competences"] = [
            dict(item) for item in motor_competences if isinstance(item, Mapping)
        ]
        organism_facts.append("motor_competences")
    if effects is not None:
        snapshot["effects"] = [
            dict(item) for item in effects if isinstance(item, Mapping)
        ]
        organism_facts.append("effects")
    if "embodiment" in snapshot and "bindings" in snapshot["embodiment"]:
        organism_facts.append("embodiment.bindings")
    if outcome is not None:
        snapshot["outcome"] = dict(outcome)
        organism_facts.append("outcome")
    if observer_analysis:
        snapshot["observer_analysis"] = observer_analysis
        if "activationClasses" in observer_analysis:
            observer_derived.append("observer_analysis.activationClasses")
        if "predictionErrors" in observer_analysis:
            observer_derived.append("observer_analysis.predictionErrors")
    if observer_semantics:
        snapshot["observer_semantics"] = observer_semantics
        if "sensory" in observer_semantics:
            observer_derived.append("observer_semantics.sensory")
        if "motor" in observer_semantics:
            observer_derived.append("observer_semantics.motor")

    if organism_facts or observer_derived:
        snapshot["provenance"] = {
            "organismFacts": organism_facts,
            "observerDerived": observer_derived,
        }

    if rich_state.get("tick") is not None:
        try:
            snapshot["tick"] = int(rich_state["tick"])
        except (TypeError, ValueError):
            pass
    if rich_state.get("organism_id") is not None:
        snapshot["display_id"] = str(rich_state["organism_id"])

    details: dict[str, Any] = {}
    if runtime.get("investigated_capability") is not None:
        details["investigatedCapability"] = runtime["investigated_capability"]
    if runtime.get("evidence_gathered") is not None:
        try:
            details["evidenceGathered"] = int(runtime["evidence_gathered"])
        except (TypeError, ValueError):
            pass
    if runtime.get("homeostatic_deviation") is not None:
        try:
            details["homeostaticDeviation"] = float(runtime["homeostatic_deviation"])
        except (TypeError, ValueError):
            pass
    raw_events = runtime.get("runtime_events")
    if isinstance(raw_events, (list, tuple)):
        details["runtimeEvents"] = [str(item) for item in raw_events[-32:]]
    raw_signal_knowledge = runtime.get("signal_knowledge")
    if isinstance(raw_signal_knowledge, (list, tuple)):
        discovery_counts: dict[str, int] = {}
        profile_count = 0
        for item in raw_signal_knowledge:
            if not isinstance(item, Mapping):
                continue
            profile_count += 1
            raw_claims = item.get("claims")
            if isinstance(raw_claims, (list, tuple)):
                for claim in raw_claims:
                    if not isinstance(claim, Mapping):
                        continue
                    raw_status = claim.get("status")
                    if raw_status is None:
                        continue
                    key = str(getattr(raw_status, "value", raw_status))
                    discovery_counts[key] = discovery_counts.get(key, 0) + 1
        if profile_count:
            details["sensoryKnowledgeProfiles"] = profile_count
        if discovery_counts:
            details["sensoryDiscoveryCounts"] = discovery_counts
    if details:
        snapshot["details"] = details

    return snapshot
