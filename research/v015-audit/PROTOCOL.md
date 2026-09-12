# Protocolo v0.15

Objetivo: verificar correcciones metodológicas y reevaluar atención, clasificación
y herencia. Versión objetivo: `05dc68c` (merge v0.15); el checkout ya estaba en
v0.16 al iniciar. No atribuir estos resultados a v0.16 ni mezclar versiones.

Fuente aislada mediante `git archive`; el runner comprueba todos los archivos
Python importados contra el commit y guarda hashes. No se modifica el motor.

- Nueve escenarios × semillas 3,7,11,17,23 × 100 hosts × 300 pasos.
- Cinco linajes independientes × tres generaciones × heredado/control ×
  100 hosts × 300 pasos. Total principal: 75 simulaciones, 2.250.000 eventos.
- Ablaciones temporales y restauradas: curiosidad anulada, creencia colectiva
  neutral `(0.5,0)`, confianza fija. Las otras condiciones cambian parámetros.
- Guardar métricas canónicas, breakdown por familia/fase/deriva, hashes completos
  del mundo y hashes de etiquetas, sin usar verdad en decisiones de agentes.
- Verificar igualdad de mundos en cada pareja longitudinal y generación 1 sin
  herencia como control de paridad. Promediar efectos de generaciones 2–3 dentro
  de cada linaje y luego entre linajes; no contar generaciones como independientes.
- Resultados exploratorios: medias, rangos y consistencia entre cinco semillas;
  no probabilidades de verdad ni afirmaciones de significación estadística.
- No comparar directamente porcentajes con v0.14: la separación de RNG cambia
  los mundos generados con una misma semilla.

```bash
mkdir -p /tmp/symbiont-audit-05dc68c
git archive 05dc68c | tar -x -C /tmp/symbiont-audit-05dc68c
PYTHONPATH=/tmp/symbiont-audit-05dc68c/src .venv/bin/python \
  research/v015-audit/run.py --mode single --output /tmp/v015-single.jsonl
PYTHONPATH=/tmp/symbiont-audit-05dc68c/src .venv/bin/python \
  research/v015-audit/run.py --mode longitudinal --output /tmp/v015-longitudinal.jsonl
```

Los destinos deben ser nuevos. El proceso trabaja sobre el commit congelado,
aunque el repositorio siga evolucionando. No se escribe en `.symbiont/`.

## Seguimiento motivado por la auditoría

Tras reproducir que poisoning modifica también rasgos de agentes, se añadieron
10 ejecuciones: fracciones 0 y 0.30 con los rasgos de baseline fijados, sobre las
mismas cinco semillas. `controlled_poison.py` conserva las asignaciones invertidas
pero reemplaza solo los tres rasgos de decisión. No es una corrección del motor.
Total válido del estudio completo: 85 simulaciones y 2.550.000 eventos.
La salida longitudinal válida es `longitudinal-complete.jsonl`; el archivo
`longitudinal.jsonl` contiene únicamente el encabezado del intento fallido del
observador y debe excluirse de cualquier agregación.
