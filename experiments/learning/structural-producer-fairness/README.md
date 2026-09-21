# Structural producer fairness stress

This protocol tests the scheduler in isolation from embodied learning.

Four continuously active opaque producers compete for structural admission. One
producer attempts to expose 1,000 simultaneous hypotheses. Backpressure must
collapse that multiplicity to one global nominee.

The test records the exact service schedule and verifies a hard fairness bound:
with P continuously active producers, no producer may wait more than P-1
completed arbitration rounds between opportunities.

This is an infrastructure property, not a cognitive utility test. It does not
claim that proposals deserve to survive after admission.
