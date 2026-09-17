from __future__ import annotations

from typing import Any, Callable

from symbiont.simulation import run_simulation
from symbiont_lab.studies.attention.causal import run_causal_attention_budget
from symbiont_lab.studies.attention.replicated import run_causal_budget_study
from symbiont_lab.studies.attention.retrospective import run_attention_budget
from symbiont_lab.studies.evidence.causal_budget import run_replicated_causal_evidence_study
from symbiont_lab.studies.evidence.noise_sweep import run_evidence_noise_sweep
from symbiont_lab.studies.evidence.replicated import run_replicated_evidence_study
from symbiont_lab.studies.evidence.second_look import run_second_look_study
from symbiont_lab.studies.continuity.recurrent_restoration import run_recurrent_restoration_study
from symbiont_lab.studies.heritage.ecological_shift import run_ecological_shift_study
from symbiont_lab.studies.heritage.longitudinal import run_longitudinal_study
from symbiont_lab.studies.heritage.replicated import run_replicated_heritage_stress_study
from symbiont_lab.studies.heritage.stress import run_heritage_stress_study
from symbiont_lab.studies.learning.predictive_utility import run_predictive_utility_study
from symbiont_lab.studies.learning.private_model_utility import run_private_model_utility_study
from symbiont_lab.studies.learning.private_model_controls import run_private_model_controls_study
from symbiont_lab.studies.learning.private_model_regime_shift import run_private_model_symmetric_regime_study
from symbiont_lab.studies.learning.private_model_adaptation import run_private_model_adaptation_study
from symbiont_lab.studies.learning.cultural_foundation import run_cultural_foundation_study


def run_comparative_study(*args: Any, **kwargs: Any) -> Any:
    """Lazy import avoids the experiments/studies package cycle at collection."""
    if not args and "base_spec" not in kwargs:
        raise ValueError("campaign.comparative requires base_spec")
    from symbiont_lab.studies.campaigns.comparative import run_comparative_study as implementation
    return implementation(*args, **kwargs)


PROTOCOLS: dict[str, Callable[..., Any]] = {
    "simulate": run_simulation,
    "attention.retrospective": run_attention_budget,
    "attention.causal": run_causal_attention_budget,
    "attention.replicated": run_causal_budget_study,
    "evidence.second-look": run_second_look_study,
    "evidence.replicated": run_replicated_evidence_study,
    "evidence.noise-sweep": run_evidence_noise_sweep,
    "evidence.causal-budget": run_replicated_causal_evidence_study,
    "heritage.longitudinal": run_longitudinal_study,
    "heritage.stress": run_heritage_stress_study,
    "heritage.replicated": run_replicated_heritage_stress_study,
    "heritage.ecological-shift": run_ecological_shift_study,
    "campaign.comparative": run_comparative_study,
    "learning.predictive-utility": run_predictive_utility_study,
    "learning.private-model-utility": run_private_model_utility_study,
    "learning.private-model-controls": run_private_model_controls_study,
    "learning.private-model-regime-symmetric": run_private_model_symmetric_regime_study,
    "learning.private-model-adaptation": run_private_model_adaptation_study,
    "learning.cultural-foundation": run_cultural_foundation_study,
    "continuity.recurrent-restoration": run_recurrent_restoration_study,
}


def get_protocol(name: str) -> Callable[..., Any]:
    if name not in PROTOCOLS:
        valid = ", ".join(sorted(PROTOCOLS.keys()))
        raise ValueError(f"Unknown protocol: '{name}'. Available protocols: {valid}")
    return PROTOCOLS[name]
