# Genome v2 — arquitectura implementada

**Estado:** implementado en core y adaptadores principales  
**Propósito:** separar genotipo, expresión, desarrollo, experiencia y embodiment como mecanismos causales distintos.

## Invariantes

1. Existe una única representación genética operativa: `symbiont.genetics.Genome`.
2. `genotype_hash` identifica contenido genético; genealogía e identidad de reproducción viven fuera del genotipo.
3. El body no modifica el Genome y el Genome no contiene anatomía, número de actuadores, salud corporal ni edad.
4. `KernelLimits` sigue siendo un techo computacional externo y no heredable.
5. La capacidad heredada es un techo desarrollable; la capacidad efectiva del grafo crece durante la ontogenia.
6. `GeneExpressionState` es estado adquirido de vida, persistente pero no heredable.
7. Evidencia observada hasta el tick t sólo puede modificar la expresión efectiva del tick t+1.
8. No existe un segundo regulador de metaplasticidad: `ExpressionRegulator` es la ruta canónica.
9. Epigenética adquirida está desactivada por defecto y sólo existe bajo `EpigeneticProtocol` explícito.
10. Ningún locus canónico existe sin binding auditable a un consumidor, proyección observable y prueba causal.
11. Re-embodiment conserva Genome y cognición general, pero el conocimiento motor queda scoped al contrato opaco del body.
12. Un `MotorPrimitive` sólo es válido sobre el `ActuatorSurface.contract_fingerprint` en el que fue aprendido.

## Flujo causal

```text
Genome
  |
  v
ExpressionState(t)
  |
  +--> cognition / plasticity / structural development
  |
  +--> exploration
  |
  v
action A(t)
  |
  v
body + environment
  |
  v
observation S(t+1)
  |
  +--> prediction error
  +--> novelty
  +--> controllability loss
  +--> body-model contradiction
  +--> resource pressure
  |
  v
RegulatorySignals(t+1)
  |
  v
ExpressionState(t+1)
```

El fingerprint técnico del contrato corporal **no** entra en `RegulatorySignals`. Sólo se utiliza para seguridad, persistencia y compatibilidad de conocimiento motor.

## Familias genéticas canónicas

### Development

- `soft_node_budget`
- `soft_edge_budget`
- `sense_node_budget`
- `capacity_growth_sensitivity`
- `consolidation_interval_ticks`

Los budgets son techos ontogenéticos, no capacidad concedida al nacer.

### Plasticity

- rango adaptativo de `learning_rate`
- `eligibility_decay`
- rango adaptativo de `structural_plasticity`

### Regulation

- `uncertainty_gain`
- `novelty_gain`
- `prediction_error_gain`
- `controllability_loss_gain`
- `embodiment_mismatch_gain`
- `regulation_smoothing`
- `regulation_decay`

### Sensorimotor

- `spontaneous_activity_baseline`
- `uncertainty_exploration_gain`
- `prediction_error_exploration_gain`
- `exploration_habituation`
- `reacclimation_sensitivity`

### Structure

- rango adaptativo de `growth_threshold`
- rango adaptativo de `pruning_threshold`
- `minimum_support`
- `tentative_lifetime_ticks`

### Evolvability

- multiplicador de mutación por familia
- `recombination_linkage`

La escala efectiva de mutación es:

```text
schema mutation scale
x
inherited family multiplier
```

Los grupos de recombinación pertenecen al schema; la propensión heredable a conservarlos o romperlos pertenece al Genome.

## Loci deliberadamente no incluidos

Genome v2 no incluye todavía:

- forgetting-rate adaptativo;
- consolidation-sensitivity adaptativa;
- contingency window/sensitivity genética;
- controllability sensitivity genética;
- body-schema adaptation rate genética;
- complexity pressure genética;
- parámetros epigenéticos como genes.

Estas ideas permanecen fuera del schema porque todavía no disponen de un consumidor causal único y verificable en el runtime actual. Se incorporarán sólo cuando exista mecanismo, telemetría y estudio de ablación.

## Body y actuación

`ActuatorSurface` pertenece al embodiment.

```text
Body
  |
  v
ActuatorSurface
  |- opaque actuator ids
  |- physical cost/health/threshold
  '- contract_fingerprint
        |
        v
     Symbiont
```

No existe:

```text
Body -> MotorGenes -> Genome
```

`MotorGenes` queda únicamente como constructor fail-fast para detectar callers legacy.

## Persistencia

Checkpoint separa:

```text
genome
gene_expression
germline
acquired cognition
body-owned actuation surface
embodiment-scoped sensorimotor knowledge
```

Checkpoints Genome v1 son verificados con su hash histórico antes de migrarse. `HeritableGenome` histórico se proyecta una sola vez sobre loci v2 que todavía tienen significado causal; los demás se descartan en vez de convertirse en configuración muerta.

Sensorimotor v10 añade `embodiment_fingerprint`. Checkpoints v9 pueden vincularse una sola vez a un body actual ya validado. Pre-v9 falla cerrado.

## Re-embodiment

Cambio A -> B:

- Genome permanece idéntico.
- Genealogy permanece idéntica.
- experiencia/cognición general permanece.
- body state se reinicia según el nuevo embodiment.
- primitivas de A dejan de tener autoridad sobre B.
- pérdida de predicción/controlabilidad eleva regulación y exploración de forma endógena.

Retorno B -> A:

- memoria longitudinal sólo recupera hipótesis del mismo lifecycle contract;
- cada hipótesis motora debe además coincidir con el motor-surface fingerprint;
- vuelve como hipótesis histórica sin autoridad y requiere nueva evidencia.

## Regla constitucional de nuevos genes

Un locus nuevo sólo entra en `DEFAULT_GENOME_SCHEMA` si tiene simultáneamente:

1. consumidor causal;
2. binding único en `canonical_gene_bindings()`;
3. telemetría/proyección observable;
4. test de mutación/causalidad;
5. hipótesis experimental falsable.

La existencia de una idea biológicamente plausible no es suficiente para convertirla en gen.
