from __future__ import annotations

from symbiont_lab.server.server import make_server
from symbiont_lab.server.state import ExperimentRunState, StudyRunState


def test_server_instantiation():
    exp_state = ExperimentRunState()
    std_state = StudyRunState()
    # Test that HTTP server can bind to ephemeral port (0)
    server = make_server(host="127.0.0.1", port=0, experiment_state=exp_state, study_state=std_state)
    try:
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_address[1] > 0
    finally:
        server.server_close()
