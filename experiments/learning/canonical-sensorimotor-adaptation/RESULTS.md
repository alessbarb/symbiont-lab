# Resultados observados

## Ejecución

Comando equivalente:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
from symbiont_lab.studies.learning.canonical_sensorimotor_adaptation import (
    run_sensorimotor_adaptation_study,
)

result = run_sensorimotor_adaptation_study(
    seeds=(101, 127, 149),
    warmup_ticks=64,
    horizon_ticks=96,
)
print(result.as_dict())
PY
```

Resultado reproducido el 2026-09-21:

| semilla | divergencia sensorial media | entrega intacta | entrega dañada | primitivas nuevas dañadas | primitivas nuevas reproducidas | primitivas conocidas reproducidas | canales máximos | gate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 101 | 0.267600 | 46 | 0 | 29 | 3 | 1 | 17 | pasa |
| 127 | 0.185683 | 47 | 0 | 29 | 2 | 1 | 22 | pasa |
| 149 | 0.260446 | 73 | 0 | 5 | 3 | 1 | 16 | pasa |

Las tres semillas pasan: `validated_trials=3`, `validated=true`. Las tres
continuaciones parten del mismo estado físico y cognitivo emparejado, la
lesión sólo afecta a un actuador opaco y el aparato no modifica el modelo
interno del organismo.

## Interpretación limitada

Esto valida **adaptación sensorimotora local** bajo una lesión reproducible:
el organismo pierde la entrega en el actuador dañado, observa una trayectoria
sensorial distinta, reutiliza una primitiva previa y cambia su conjunto de
primitivas, incluyendo fragmentos multicanal.

No valida todavía una red neuronal nueva, causalidad explícita, composición
conceptual, transferencia a una tarea no vista, locomoción ni integración
canónica en todo Symbiont. Es evidencia para conservar este mecanismo como
experimento candidato, no autorización para sustituir `CognitiveGraph` ni
para promoverlo a comportamiento motor.
