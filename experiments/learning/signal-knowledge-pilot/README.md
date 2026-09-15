# Piloto de diseño de conocimiento de señales

Artefacto sintético previo al motor; no observa el host, no importa verdad del
evaluador en `symbiont` y no demuestra aceptación del runtime ni de Observatory.

```bash
.venv/bin/python experiments/learning/signal-knowledge-pilot/pilot.py > /tmp/signal-pilot.json
.venv/bin/python -m pytest experiments/learning/signal-knowledge-pilot/test_pilot.py -q
.venv/bin/python experiments/learning/signal-knowledge-pilot/budget.py
```

## Protocolo ensayado

Semillas de piloto 17, 29, 43; 1152 ticks por ejecución. Regresión ridge con
intercepto sobre las últimas 64 transiciones resueltas. Predice diferencia de B
con dos diferencias propias y añade diferencia de A para el candidato. Primeras
32 transiciones solo entrenan. Pérdida cuadrática de residual normalizado por
desviación de B observada hasta emitir la predicción, truncado a magnitud 4.
Referencias: cero, media de últimas 64 lecturas, persistencia y regresión propia.
No se selecciona retrospectivamente una referencia desfavorable.

Épocas no solapadas de 64 ticks; al menos 48 comparables, ventaja relativa ≥15%
y absoluta ≥0.01 contra **cada** referencia. Tres épocas consecutivas promueven;
dos épocas comparables fallidas contradicen. El piloto evalúa pares predefinidos:
no valida todavía la selección adaptativa ni asociaciones síncronas.

## Resultado observado

`results.json` conserva configuración, pérdidas por referencia y época, trials,
censurado, promociones y contradicciones para las 126 ejecuciones.

| Entorno | Ejecuciones | Alguna promoción | Alguna contradicción | Apoyo final |
|---|---:|---:|---:|---:|
| Constante | 3 | 0 | 0 | 0 |
| Ruido independiente | 3 | 0 | 0 | 0 |
| Autocorrelación positiva | 3 | 0 | 0 | 0 |
| Autocorrelación negativa | 3 | 0 | 0 | 0 |
| Retardo verdadero | 3 | 3 | 0 | 3 |
| Fuente común simultánea | 3 | 0 | 0 | 0 |
| Tendencias compartidas | 3 | 0 | 0 | 0 |
| Retardo con huecos | 3 | 1 | 0 | 1 |
| Retardo que desaparece | 3 | 3 | 3 | 0 |
| Retardo con escala y desplazamiento | 3 | 3 | 0 | 3 |
| 32 pares de ruido por semilla | 96 | 0 | 0 | 0 |

Los huecos reducen observaciones consecutivas y épocas con cobertura suficiente;
no se rebaja el umbral para forzar descubrimiento. Este resultado limita la
sensibilidad con muestreo escaso. Cero promociones en estos negativos no es una
garantía estadística universal ni una corrección formal de comparaciones múltiples.
El estudio de aceptación usará semillas 101, 127, 149 sin recalibrar con ellas.

## Integridad y presupuesto

Cinco pruebas pasan: ajuste lineal conocido, independencia del futuro de épocas
ya cerradas, censura de objetivo ausente, rechazo de constantes y determinismo.
No prueban todos los estados que tendrá el motor de producción.

La fixture de `budget.py` serializa 64 perfiles, 192 claims y 64 eventos en
215577 bytes (JSON UTF-8 compacto). Se fija un subpresupuesto de 256 KiB para
conocimiento y otro de 256 KiB para su proyección con eventos. El techo host
existente continúa en 2 MiB. La fixture no mide RSS ni el resto del checkpoint:
el ensayo integrado deberá medir el bloque real, host completo y journal, sin
confundir esta reserva de diseño con una validación real de memoria del motor.
