from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from symbiont_lab.archive.runs import ExperimentArchive
from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.experiments.spec import ExperimentSpec
from .api import make_handler
from .state import DashboardState, StudyDashboardState, start_experiment, start_study


def _spec_from_args(args: argparse.Namespace) -> ExperimentSpec:
    return ExperimentSpec(
        title=args.title,
        hypothesis=args.hypothesis,
        success_criteria=args.success_criteria,
        notes=args.notes,
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        delay=max(args.delay, 0.0),
    )


def make_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    experiment_state: DashboardState | None = None,
    study_state: StudyDashboardState | None = None,
) -> ThreadingHTTPServer:
    exp_state = experiment_state or DashboardState()
    std_state = study_state or StudyDashboardState()

    experiment_starter = lambda spec: start_experiment(exp_state, std_state, spec)
    study_starter = lambda spec, **kwargs: start_study(
        exp_state,
        std_state,
        spec,
        **kwargs,
    )

    return ThreadingHTTPServer(
        (host, port),
        make_handler(exp_state, std_state, experiment_starter, study_starter),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch and visualize Symbiont Lab experiments and studies")
    parser.add_argument("--title", default="Dashboard experiment")
    parser.add_argument("--hypothesis", default="")
    parser.add_argument("--success-criteria", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--delay", type=float, default=0.04)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--archive", default=".symbiont/experiments.jsonl")
    parser.add_argument("--study-archive", default=".symbiont/studies.jsonl")
    parser.add_argument("--no-record", action="store_true")
    parser.add_argument("--no-autorun", action="store_true")
    args = parser.parse_args()

    initial_spec = _spec_from_args(args)
    archive = None if args.no_record else ExperimentArchive(args.archive)
    study_archive = None if args.no_record else StudyArchive(args.study_archive)
    experiment_state = DashboardState(archive=archive)
    experiment_state.spec = initial_spec
    study_state = StudyDashboardState(archive=study_archive)

    experiment_starter = lambda spec: start_experiment(experiment_state, study_state, spec)
    if not args.no_autorun:
        experiment_starter(initial_spec)

    server = make_server(
        host="127.0.0.1",
        port=args.port,
        experiment_state=experiment_state,
        study_state=study_state,
    )
    print(f"Symbiont Lab dashboard: http://127.0.0.1:{args.port}")
    print(f"Research archive: {archive.path}" if archive else "Research archive disabled.")
    print(f"Study archive: {study_archive.path}" if study_archive else "Study archive disabled.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
