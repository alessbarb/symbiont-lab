import re
content = open('src/symbiont/core/cognition/agent.py').read()

# Add import
content = content.replace(
    'from .memory import AgentMemory, Episode',
    'from .memory import AgentMemory, Episode\nfrom ..social.ledger import SocialEvidenceLedger, SourceEvidenceOutcome'
)

# Update assess signature
content = content.replace(
    'def assess(self, obs: Observation) -> Assessment:',
    'def assess(self, obs: Observation, ledger: SocialEvidenceLedger | None = None) -> Assessment:'
)

# Insert curiosity boost calculation
boost_code = """
        social_interest = 0.0
        if ledger is not None:
            for claim in ledger.unresolved_claims():
                # Rough matching: if the claim payload matches the fingerprint
                if claim.payload == fp:
                    social_interest = 0.35
                    break
        
        information_gain = novelty + social_interest
        curiosity = min(
            1.0,
            (novelty + social_interest) * uncertainty * information_gain * max(relevance, 0.05) * self.curiosity_scale,
        )
"""
content = re.sub(
    r'        information_gain = novelty\n        curiosity = min\([\s\S]*?        \)\n',
    boost_code,
    content
)

# Update observe signature
content = content.replace(
    'def observe(self, step: int, obs: Observation) -> Assessment:',
    'def observe(self, step: int, obs: Observation, ledger: SocialEvidenceLedger | None = None) -> Assessment:'
)
content = content.replace(
    'assessment = self.assess(obs)',
    'assessment = self.assess(obs, ledger)'
)

# Record reconciliation
recon_code = """
        if assessment.should_investigate:
            self.investigated += 1
            self.memory.remember(
                Episode(
                    step=step,
                    fingerprint=assessment.fingerprint,
                    curiosity=assessment.curiosity,
                    risk=assessment.risk,
                    believed_threat=assessment.believes_threat,
                )
            )
            if ledger is not None:
                outcome = SourceEvidenceOutcome.AGREEMENT if assessment.believes_threat else SourceEvidenceOutcome.CONTRADICTION
                for claim in ledger.unresolved_claims():
                    if claim.payload == assessment.fingerprint:
                        ledger.record_local_reconciliation(
                            claim_id=claim.claim_id,
                            tick=step,
                            outcome=outcome,
                            compatibility=1.0 - assessment.novelty,
                            quality=1.0 - assessment.uncertainty,
                            freshness=1.0,
                            evidence_ref=f"episode-{step}"
                        )
"""
content = re.sub(
    r'        if assessment\.should_investigate:\n            self\.investigated \+= 1\n            self\.memory\.remember\([\s\S]*?            \)\n',
    recon_code,
    content
)

open('src/symbiont/core/cognition/agent.py', 'w').write(content)
