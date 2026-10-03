from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "lab" / "src" / "lab" / "workbench" / "web"


def _read(relative: str) -> str:
    return (WEB_ROOT / relative).read_text(encoding="utf-8")


def test_shell_uses_native_landmarks_and_focusable_view_root():
    html = _read("app.html")
    assert '<nav class="rail" aria-label="Main navigation">' in html
    assert 'role="navigation"' not in html
    assert 'role="main"' not in html
    assert '<main id="view-root" tabindex="-1"></main>' in html
    assert 'class="skip-link"' in html
    assert "github.com/alessbarb/symbiont-lab" in html


def test_live_region_is_scoped_to_runtime_state_not_entire_footer():
    html = _read("app.html")
    assert '<footer class="statusbar">' in html
    assert 'class="statusbar-state"' in html
    assert 'id="sb-status" class="sb-item" role="status" aria-live="polite"' in html
    assert '<footer class="statusbar" role="status"' not in html


def test_router_is_declarative_and_polling_is_not_interval_based():
    app = _read("app.js")
    assert "const ROUTES = {" in app
    assert "RuntimeStatePoller" in app
    assert "setInterval(" not in app
    assert "removeAttribute('aria-current')" in app
    assert "history.pushState" in app
    assert "popstate" in app


def test_runtime_poller_prevents_overlap_and_handles_visibility():
    runtime = _read("runtime-state.js")
    assert "if (!this.running || this.controller) return;" in runtime
    assert "new AbortController()" in runtime
    assert "visibilitychange" in runtime
    assert "document.hidden" in runtime
    assert "maxBackoffMs" in runtime


def test_all_top_level_views_have_uniform_lifecycle_contract():
    for relative in (
        "views/home.js",
        "views/lab.js",
        "views/archive.js",
        "views/mind.js",
        "views/body.js",
        "views/vision.js",
    ):
        source = _read(relative)
        assert "export function mount" in source or "export async function mount" in source, (
            relative
        )
        assert "export function update" in source, relative
        assert "export function unmount" in source, relative


def test_body_camera_controls_are_outside_three_renderer():
    viewer = _read("views/body/viewer.js")
    controls = _read("views/body/camera-controls.js")
    assert "mountBodyCameraControls" in viewer
    assert "body-camera-button" in controls
    assert "this.followButton.style.cssText" not in viewer


def test_package_data_contains_nested_workbench_modules():
    pyproject = (REPO_ROOT / "lab" / "pyproject.toml").read_text(encoding="utf-8")
    for pattern in (
        '"web/views/body/*.js"',
        '"web/views/world/*.js"',
        '"web/views/embodiment/*.js"',
        '"web/views/lab/*.js"',
        '"web/views/archive/*.js"',
        '"web/views/shared/*.js"',
        '"web/views/mind/*.js"',
    ):
        assert pattern in pyproject


def test_server_sets_browser_security_headers():
    api = (REPO_ROOT / "lab" / "src" / "lab" / "server" / "api.py").read_text(encoding="utf-8")
    assert '"Content-Security-Policy"' in api
    assert '"X-Frame-Options", "DENY"' in api
    assert "\"frame-ancestors 'none'\"" in api


def test_mind_uses_real_tab_semantics():
    layout = _read("views/mind/layout.js")
    tabs = _read("views/mind/tab-controller.js")
    assert "setAttribute('role', 'tablist')" in layout
    assert "setAttribute('role', 'tab')" in layout
    assert "setAttribute('aria-selected'" in layout
    assert "setAttribute('role', 'tabpanel')" in layout
    assert "aria-pressed" not in tabs


def test_body_unmount_releases_browser_and_gpu_resources():
    viewer = _read("views/body/viewer.js")
    for required in (
        "cancelAnimationFrame(this.rafId)",
        "this.sse.close()",
        "this.resizeObs.disconnect()",
        "this.controls.dispose()",
        "this.renderer.dispose()",
        "this.workspace?.dispose()",
    ):
        assert required in viewer


def test_mind_unmount_releases_streams_animation_and_observer():
    mind = _read("views/mind.js")
    for required in (
        "cognition.stop()",
        "_streams.close()",
        "_resizeObs.disconnect()",
        "resetPresentation()",
    ):
        assert required in mind


def test_cognition_inspector_does_not_render_snapshot_data_with_inner_html():
    cognition = _read("views/mind/cognition-controller.js")
    assert "innerHTML" not in cognition


def test_mind_layout_is_structural_not_inline_styled():
    layout = _read("views/mind/layout.js")
    assert ".style.cssText" not in layout
    assert "innerHTML" not in layout


def test_identity_sensory_only_keeps_data_driven_inline_styles():
    identity = _read("views/mind/identity-sensory.js")
    assert "innerHTML" not in identity
    # Dynamic visual encodings remain legitimate: confidence/health dots and
    # percentage bars depend on the current snapshot.
    assert identity.count("style.cssText") <= 1


def test_view_specific_css_is_split_from_app_shell():
    html = _read("app.html")
    app_css = _read("app.css")
    assert 'href="/assets/body.css"' in html
    assert 'href="/assets/mind.css"' in html
    assert (WEB_ROOT / "body.css").is_file()
    assert (WEB_ROOT / "mind.css").is_file()
    assert len(app_css) < 20000


def test_cognition_inspector_is_extracted_from_controller():
    controller = _read("views/mind/cognition-controller.js")
    inspector = _read("views/mind/cognition-inspector.js")
    assert "createCognitionInspector" in controller
    assert "function renderCognitionInspector" not in controller
    assert "function renderCognitionInspector" in inspector


def test_cognition_renderer_keeps_shared_graph_helpers():
    controller = _read("views/mind/cognition-controller.js")
    assert "function focusedSectorContext()" in controller
    assert "function currentRenderedTopology()" in controller
    assert "graphSubgraphIds" in controller


def test_mind_generative_cognition_is_separate_from_atlas_topology():
    layout = _read("views/mind/layout.js")
    controller = _read("views/mind/cognition-controller.js")
    css = _read("mind.css")
    physics_runtime = (REPO_ROOT / "lab" / "src" / "lab" / "physics3d" / "runtime.py").read_text(
        encoding="utf-8"
    )
    projection = (REPO_ROOT / "lab" / "src" / "lab" / "observation" / "projection.py").read_text(
        encoding="utf-8"
    )

    assert "mind-cognition-generative" in layout
    assert "mind-cognition-generative-body" in layout
    assert "mind-cognition-right-rail" in layout
    assert ".mind-cognition-right-rail" in css
    assert "source?.cognition?.generative" in controller
    assert "renderGenerativePanel(source)" in controller
    # The panel's wording comes from the observability-state contract, which
    # names why a snapshot is or is not there (issue #277).
    assert "classifyObservability(" in controller
    assert "observability.label" in controller
    assert "Generative resident not observed" not in controller
    assert "mind-generative-history" in controller
    assert "mind-generative-flow" in controller
    assert '"generative_status"' in physics_runtime
    assert 'mind_cognition["generativeStatus"]' in projection
    assert '"generative"' in physics_runtime
    assert 'mind_cognition["generative"]' in projection
    assert "completeTopology.nodes.push" not in controller
    assert "rawNodes.push" not in controller


def test_cognition_causal_provenance_is_observer_only_and_on_demand():
    client = _read("views/mind/causal-provenance.js")
    controller = _read("views/mind/cognition-controller.js")
    inspector = _read("views/mind/cognition-inspector.js")

    assert "/api/provenance/why?" in client
    assert "provenanceRefForNode" in client
    assert "fetchCausalProvenance" in controller
    assert "loadSelectedCausalProvenance" in controller
    assert "Causal history" in inspector
    assert "never fed back" in inspector
    assert "innerHTML" not in client


def test_atlas_layout_uses_structural_relations_and_collapses_dormant_registries():
    semantics = _read("views/mind/relation-semantics.js")
    sectors = _read("views/mind/functional-sectors.js")
    model = _read("views/mind/graph-model.js")
    lod = _read("views/mind/cognitive-lod.js")
    controller = _read("views/mind/cognition-controller.js")

    assert "'causal_estimate'" in semantics
    assert "'affords'" in semantics
    assert "'intends_with'" in semantics
    assert "'anticipates'" in semantics
    assert "if (!isStructuralAtlasEdge(edge)) continue;" in sectors
    assert "projectedAdjacency" in model
    assert "structuralDegree" in model
    assert "structurallyDisconnected" in model
    assert "finite(node.degree, 0) > 0" in lod
    assert "Dormant registry" not in lod
    assert "nodes.filter(node => finite(node.degree, 0) > 0)" in lod
    assert "physicsNodes = nodes.filter" in controller
    assert "if (!isStructuralAtlasEdge(edge)) continue;" in controller


def test_atlas_overlay_satellites_stay_local_without_becoming_structure():
    model = _read("views/mind/graph-model.js")
    controller = _read("views/mind/cognition-controller.js")
    inspector = _read("views/mind/cognition-inspector.js")

    assert "overlayOnly" in model
    assert "fringeStructural" in model
    assert "satelliteHostId" in model
    assert "satelliteHasStructuralHost" in model
    assert "projectedAdjacency" in model
    assert "Overlay-only edges get a local tether" in controller
    assert "raw.fringeStructural" in controller
    assert "node.overlayOnly" in controller
    assert "node.fringeStructural" in controller
    assert "0.020 + confidence * 0.010" in controller
    assert "evidence satellite" in inspector
    assert "structural fringe" in inspector


def test_world_is_extracted_from_embodiment_domain():
    """ADR-0008: the UI no longer presents World as part of Body/Embodiment."""
    html = _read("app.html")
    app = _read("app.js")
    workspace = _read("views/body/workspace.js")
    viewer = _read("views/body/viewer.js")

    assert 'href="#embodiment"' in html and 'href="#world"' in html
    assert 'href="#body"' not in html
    assert "body: 'embodiment'" in app  # old links keep working
    assert "options: { domain: 'embodiment' }" in app
    assert "options: { domain: 'world' }" in app

    embodiment_tabs = workspace.split("embodiment: [", 1)[1].split("],\n  world:", 1)[0]
    for world_only in ("'world'", "'motion'", "'interaction'", "'history'", "'overview'"):
        assert world_only not in embodiment_tabs
    assert "'Acquired Self'" in embodiment_tabs
    assert "In World" not in workspace

    assert "this.domain === 'world' ? new WorldView(this) : null" in viewer
    assert "this.domain === 'world' && Array.isArray(data.resource_position)" in viewer
    assert (WEB_ROOT / "views" / "world" / "world-view.js").is_file()
    assert not (WEB_ROOT / "views" / "body" / "world-view.js").exists()


def test_home_launches_explicit_run_definitions():
    home = _read("views/home.js")
    assert "/api/run-definitions" in home
    assert "definition_id: selectedDefinition" in home
    assert "item.launchable ? '' : 'disabled'" in home


def test_action_discovery_moved_from_mind_to_embodiment():
    """Gap §11 / milestone EW-B: Mind owns cognition, not motor acquisition."""
    workspace = _read("views/body/workspace.js")
    layout = _read("views/mind/layout.js")
    tabs = _read("views/mind/tab-controller.js")
    discovery = _read("views/embodiment/discovery.js")

    embodiment_tabs = workspace.split("embodiment: [", 1)[1].split("],\n  world:", 1)[0]
    assert embodiment_tabs.strip().startswith("['discovery', 'Discovery']")
    assert "Motor Learning" not in layout
    assert "'motor'" not in tabs
    assert not list((WEB_ROOT / "views" / "mind").glob("motor-learning*.js"))

    # Reuses the existing transport; subscribed only while the tab is active.
    assert "new MindStreams(" in discovery
    assert "deactivate()" in discovery and "this.streams?.close()" in discovery
    assert "else this.discovery.deactivate();" in workspace
    assert "requestAnimationFrame" in discovery


def test_acquired_self_marks_observer_correspondence():
    self_model = _read("views/body/self-model.js")
    assert "data-observer-correspondence" in self_model
    assert "Anatomical names and the figure are observer-side" in self_model


def test_workbench_v2_navigation_matches_product_architecture():
    html = _read("app.html")
    app = _read("app.js")
    for route in ("#home", "#mind", "#embodiment", "#vision", "#world", "#archive"):
        assert f'href="{route}"' in html
    assert 'href="#experiments"' not in html
    assert "experiments: 'home'" in app
    assert "mountVision" in app


def test_world_epistemic_modes_are_acquired_compare_truth():
    workspace = _read("views/body/workspace.js")
    world_tabs = workspace.split("world: [", 1)[1].split("\n  ],", 1)[0]
    assert "['acquired', 'Acquired']" in world_tabs
    assert "['compare', 'Compare']" in world_tabs
    assert "['world', 'Observer Truth']" in world_tabs
    assert "No canonical acquired external-world model is exported yet" in workspace
    assert "fabricate knowledge" in workspace


def test_mind_primary_tabs_are_live_atlas_development():
    layout = _read("views/mind/layout.js")
    assert "label: 'Live'" in layout
    assert "label: 'Atlas'" in layout
    assert "label: 'Development'" in layout


def test_developmental_observatory_surfaces_organism_not_run_as_primary_subject():
    home = _read("views/home.js")
    overview = _read("views/mind/overview.js")
    history = _read("views/mind/history.js")
    discovery = _read("views/embodiment/action-discovery.js")
    archive = _read("views/archive.js")
    archive_render = _read("views/archive/render.js")

    assert "Current Symbiont" in home
    assert "Development now" in home
    assert "What is happening now" in overview
    assert "Recent cognitive events" in overview
    assert "How cognition is changing" in history
    assert "Developmental narrative" in history
    assert "Current causal chain" in discovery
    assert "Action" in discovery and "Observed consequence" in discovery
    assert "Evidence" in discovery and "Competence" in discovery
    assert "/api/runs" in archive and "/api/organisms" in archive
    assert "Developmental timeline" in archive_render
    assert "Symbiont continuity" in archive_render


def test_world_acquired_compare_hide_observer_body_and_explain_absence():
    workspace = _read("views/body/workspace.js")
    viewer = _read("views/body/viewer.js")
    css = _read("workbench-v2.css")
    assert "world-epistemic-stage" in workspace
    assert "No organism-owned external model yet" in workspace
    assert "Nothing to compare yet" in workspace
    assert "this.baseNode.visible = !epistemicOnly" in viewer
    assert ".world-epistemic-mode .body-camera-bar" in css


def test_vision_distinguishes_apparatus_from_active_experience():
    vision = _read("views/vision.js")
    assert "hasVisualApparatus" in vision
    assert "visionExperienceActive" in vision
    assert "VISUAL APPARATUS PRESENT" in vision
    assert "VISION EXPERIENCE LIVE" in vision
    assert "current run is not a Vision Experience" in vision


def test_observer_truth_uses_one_scene_with_inspector_overlays():
    world = _read("views/world/world-view.js")
    css = _read("workbench-v2.css")
    assert "World · Observer Truth" in world
    assert 'data-world-overlay="physical"' in world
    assert 'data-world-overlay="perception"' in world
    assert 'data-world-overlay="self"' in world
    assert "Known World" not in world.split("const LAYERS", 1)[1].split("];", 1)[0]
    assert "Predictions" not in world.split("const LAYERS", 1)[1].split("];", 1)[0]
    assert ".body-world-toolbar{display:none!important}" in css


def test_embodiment_apparatus_links_physical_region_to_acquired_self():
    workspace = _read("views/body/workspace.js")
    assert "selfViewSegmentRecord" in workspace
    assert "Acquired correspondence · observer projection" in workspace
    assert "data-open-acquired-self" in workspace
    assert "segment|" in _read("views/body/self-view.js")
    assert "Open in Acquired Self" in workspace


def test_vision_modes_are_interactive_and_passively_observed():
    vision = _read("views/vision.js")
    assert "new MindStreams" in vision
    assert "data-vision-mode" in vision
    assert "activeMode === 'apparatus'" in vision
    assert "activeMode === 'acquired'" in vision
    assert "Admitted senses · all modalities" in vision
    assert "Visual attribution is intentionally not inferred" in vision
    assert (
        "Per-receptor luminance samples are currently consumed by the runtime but are not exported"
        in vision
    )
    assert "((i * 17 + 11) % 9)" not in vision


def test_archive_development_events_link_back_to_live_contexts():
    archive = _read("views/archive/render.js")
    assert "routeForRun" in archive
    assert "data-archive-open" in archive
    assert "Open context" in archive
    assert "Open Mind" in archive


def test_acquired_self_v2_is_compare_acquired_development_not_legacy_dashboard():
    workspace = _read("views/body/workspace.js")
    acquired = _read("views/body/acquired-self-v2.js")
    self_view = _read("views/body/self-view.js")
    css = _read("workbench-v2.css")

    assert "AcquiredSelfWorkspace" in workspace
    assert "['compare', 'Compare']" in acquired
    assert "['acquired', 'Acquired']" in acquired
    assert "['development', 'Development']" in acquired
    assert "APPARATUS TRUTH" in acquired
    assert "ACQUIRED SELF" in acquired
    assert "observer correspondence only" in acquired
    assert "['uncertainty', 'Uncertainty']" in self_view
    assert ".acquired-self-compare-mode .body-data-overlay" in css


def test_acquired_self_v2_selection_is_bidirectional_between_canvas_and_projection():
    workspace = _read("views/body/workspace.js")
    viewer = _read("views/body/viewer.js")
    acquired = _read("views/body/acquired-self-v2.js")

    assert "handleCanvasSegmentPick(name)" in workspace
    assert "this.selfModel.selectSegment(name, { notifyPhysical: false })" in workspace
    assert "segmentPickRaycaster" in viewer
    assert "handleCanvasSegmentPick(event)" in viewer
    assert "data-physical-segment" in acquired
    assert "onSelectPhysical" in acquired


def test_acquired_self_v2_reembodiment_preserves_history_without_claiming_reacquisition():
    acquired = _read("views/body/acquired-self-v2.js")

    assert "priorSegmentRecords" in acquired
    assert "Embodiment changed" in acquired
    assert "STALE · not currently mapped" in acquired
    assert "RETAINED · current mapping" in acquired
    assert "NOVEL · current body" in acquired
    assert "Reacquisition is not claimed unless explicit current evidence supports it." in acquired


def test_acquired_self_v2_remains_observer_only():
    acquired = _read("views/body/acquired-self-v2.js")

    assert "never fed back to Symbiont" in acquired
    assert "Observer anatomy is only a projection surface" in acquired
    assert "fetch(" not in acquired
    assert "WebSocket" not in acquired
    assert "EventSource" not in acquired


def test_acquired_self_v21_compare_is_body_first_and_labels_are_optional():
    acquired = _read("views/body/acquired-self-v2.js")
    css = _read("workbench-v2.css")

    assert "Select the body itself." in acquired
    assert "data-toggle-regions" in acquired
    assert "data-toggle-observer-labels" in acquired
    assert "this.showRegionsFallback = false" in acquired
    assert "this.showObserverLabels = false" in acquired
    assert "Inspect evidence →" in acquired
    assert "grid-template-columns:50% 50%" in css
    assert ".labels-hidden" in css


def test_acquired_self_v22_development_uses_classified_events_and_timeline_markers():
    acquired = _read("views/body/acquired-self-v2.js")
    self_view = _read("views/body/self-view.js")

    for event_name in (
        "first_representation",
        "strengthened",
        "weakened",
        "became_stable",
        "became_uncertain",
        "agency_appeared",
        "lost_support",
    ):
        assert event_name in acquired

    assert "data-development-tick" in acquired
    assert "Session-observed events" in acquired
    assert "Structure may predate observer attachment" in acquired
    assert "self-dev-event-marker" in self_view
    assert "Observer interpretation" in self_view


def test_mind_development_distinguishes_existing_structure_from_observed_change():
    history = _read("views/mind/history.js")

    assert "Current cognitive structure" in history
    assert "Observed since" in history
    assert "Recorded change" in history
    assert "Zero change means stable during observation, not undeveloped." in history


def test_statusbar_distinguishes_live_experience_from_observatory_view():
    html = _read("app.html")
    app = _read("app.js")

    assert 'id="sb-experience"' in html
    assert 'id="sb-view"' in html
    assert "experienceLabel" in app
    assert "viewLabel" in app
    assert "setContext" in app


def test_empty_world_acquired_compare_hides_physics_canvas():
    css = _read("workbench-v2.css")

    assert ".world-epistemic-mode .body-canvas{visibility:hidden!important}" in css


def test_home_refuses_stale_physical_body_resume_and_preserves_symbiont():
    home = _read("views/home.js")

    assert "organism.resumable_body === true" in home
    assert "body_checkpoint_in_sync === false" in home
    assert "Previous body checkpoint is stale" in home
    assert "Symbiont identity and cognition are preserved" in home
    assert "selectedOrganism()?.resumable_body !== true" in home


def test_atlas_motor_mode_uses_traceable_reachability_not_node_kind_scores():
    atlas = _read("views/mind/cognitive-atlas.js")
    inspector = _read("views/mind/cognition-inspector.js")
    controller = _read("views/mind/cognition-controller.js")

    assert "export function motorReachability(" in atlas
    assert "export function isMotorNode(" in atlas
    assert "motorConnected" in atlas
    assert "motorDomain" in atlas
    assert "motorRelated" in atlas
    assert "MOTOR_NODE_KINDS" in atlas
    assert "MOTOR_EDGE_KINDS" in atlas
    assert "node.kind === 'motor_primitive' ? 0.82" not in atlas
    assert "MOTOR DOMAIN · NO OBSERVED ROUTE" in inspector
    assert "CONNECTED MOTOR ROUTE" in inspector
    assert "atlasEdgeScore(edge, graph.atlasMode, tick, graph.atlasSignals)" in controller


def test_atlas_signal_normalization_is_stable_and_indexed():
    atlas = _read("views/mind/cognitive-atlas.js")

    assert "export const ATLAS_CONFIG" in atlas
    assert "function normalizePredictionError(" in atlas
    assert "function normalizeSupport(" in atlas
    assert "function normalizeStability(" in atlas
    assert "function percentile(" in atlas
    assert "export function buildAtlasGraph(" in atlas
    assert "const nodesById = new Map(" in atlas
    assert "queue.shift()" not in atlas
    assert "Math.max(1, ...edges.map" not in atlas


def test_acquired_self_compare_uses_left_frame_viewport_and_follow_camera():
    viewer = _read("views/body/viewer.js")
    workspace = _read("views/body/workspace.js")

    assert "presentationViewportSize()" in viewer
    assert "setAcquiredSelfComparePresentation(active)" in viewer
    assert "this.compareViewportActive" in viewer
    assert "Math.floor(fullWidth * 0.5)" in viewer
    assert "this.renderer.setViewport(0, 0, width, height)" in viewer
    assert "this.renderer.setScissor(0, 0, width, height)" in viewer
    assert "this.camera.aspect = width / height" in viewer
    assert "this.followBody = true" in viewer
    assert "this.resetCameraToBody()" in viewer
    assert "setAcquiredSelfComparePresentation" in workspace


def test_motor_atlas_distinguishes_visible_routes_from_collapsed_physical_routes():
    atlas = _read("views/mind/cognitive-atlas.js")
    controller = _read("views/mind/cognition-controller.js")
    inspector = _read("views/mind/cognition-inspector.js")

    assert "motorConnectedFull" in atlas
    assert "motorCollapsedOnly" in atlas
    assert "fullMotorReachability" in controller
    assert "CONNECTED VIA COLLAPSED PHYSICAL SUBSTRATE" in inspector
    assert (
        "passes through physical actuator or embodiment structure intentionally collapsed"
        in inspector
    )


def test_atlas_controller_reuses_graph_index_for_signals_paths_and_regions():
    atlas = _read("views/mind/cognitive-atlas.js")
    controller = _read("views/mind/cognition-controller.js")

    assert "existingIndex = null" in atlas
    assert "const atlasIndex = buildAtlasGraph(enriched.nodes, enriched.edges)" in controller
    assert "index: atlasIndex" in controller
    assert "atlasIndex," in controller
    assert "renderedAtlasIndex" in controller


def test_mind_development_history_is_scoped_persistent_and_bootstrapped():
    mind = _read("views/mind.js")
    history = _read("views/mind/history.js")
    streams = _read("views/mind/streams.js")
    state = _read("views/mind/state.js")

    assert "developmentScope" in state
    assert "activateMindDevelopmentHistory" in mind
    assert "persistMindDevelopmentHistory({ force: true })" in mind
    assert "symbiont-lab:mind-development:v1:" in history
    assert "window.localStorage" in history
    assert "observedStartTick" in history
    assert "mindHistory.splice(pointIndex, 0, point)" in history
    assert "historySnapshots.splice(snapshotIndex, 0, captured)" in history
    assert "captureSnapshot: false, persist: !meta.historical" in mind
    assert "/api/organism/history?limit=256" in streams
    assert "bootstrapRecentHistory" in streams
    assert "historicalFinal" in streams
