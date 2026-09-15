"""Conservative wire-size fixture for the design, not a runtime memory benchmark."""
import json


def measure():
    profiles = []
    count = 0
    for index in range(64):
        claims = []
        for _ in range(3):
            count += 1
            claims.append(dict(
                claim_id="claim." + f"{count:064x}", subject_id="signal." + f"{index:064x}",
                object_id="signal." + f"{(index+1)%64:064x}",
                related_signal_id="signal." + f"{(index+1)%64:064x}",
                kind="synchronous_association", horizon=1, direction="unspecified",
                status="insufficient", strength_class="strong", evidence_count=2147483647,
                validation_opportunities=2147483647, improvement_class="substantial",
                revision=2147483647, reason_class="insufficient_comparable_observations",
                validation={k: 2147483647 for k in (
                    "trials", "comparable_trials", "successful_epochs", "failed_epochs")},
                epoch_classes=[[15, 15, 15, 15, 15, 64] for _ in range(4)],
                context=dict(regime_class="regime_shift", reliability_class="nominal",
                             last_tested_tick=2147483647),
            ))
        profiles.append(dict(signal_id="signal." + f"{index:064x}",
                             observed_opportunities=2147483647, valid_observations=2147483647,
                             last_observed_tick=2147483647, last_seen_age_class="long_absent",
                             claims=claims))
    events = [dict(claim_id="claim." + f"{i:064x}", tick=2147483647,
                   from_status="insufficient", to_status="supported",
                   reason_class="insufficient_comparable_observations") for i in range(64)]
    payload = dict(profiles=profiles, events=events)
    size = len(json.dumps(payload, separators=(",", ":"), allow_nan=False).encode())
    assert size <= 256 * 1024
    return dict(profiles=64, claims=count, events=64, fixture_bytes=size,
                block_budget_bytes=256 * 1024, host_budget_bytes=2 * 1024 * 1024)


if __name__ == "__main__":
    print(json.dumps(measure(), indent=2))
