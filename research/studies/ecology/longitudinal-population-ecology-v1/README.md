# Longitudinal Population Ecology v1

## Estado

Campaña de descubrimiento implementada y ejecutada localmente. No es una nueva
capacidad cognitiva y no cierra ningún fenómeno científico por sí sola.

## Diseño

Se ejecutan los stages preregistrados de `1,000` y `10,000` ticks para las
semillas `101, 127, 149`, con población fija de cuatro agentes en el simulador
canónico. Se comprueban finitud, ceilings, monotonicidad y replay determinista.
El lifecycle multigeneracional se ejecuta mediante el protocolo social-runtime
existente y se reporta por separado, porque el simulador canónico no implementa
nacimiento/muerte.

Los resultados completos están en
`experiments/learning/longitudinal-population-ecology/results.json`.

## Interpretación

Las ejecuciones largas son evidencia técnica de que estas superficies pueden
mantenerse ejecutándose bajo los límites declarados. Los patrones poblacionales
o culturales observados son candidatos descriptivos, no resultados confirmados.
No se añadió una política para producirlos ni se alteraron los gates históricos.

La ausencia de una ejecución integrada de comunicación + Private SLM +
reproducción es una limitación de composición del arnés actual. No se oculta ni
se convierte artificialmente en evidencia multigeneracional integrada.

## Resultado de discovery ejecutado

El run preregistrado ejecutó `6` combinaciones de stage/seed: `1,000` y
`10,000` ticks para las semillas `101`, `127` y `149`, con cuatro hosts. Las
seis ejecuciones terminaron en estado finito, respetaron los ceilings y
produjeron replay determinista; no se registraron anomalías. Los patrones
colectivos finales fueron, respectivamente, `28/26/30` en 1,000 ticks y
`67/60/60` en 10,000 ticks. Los contadores de episodios olvidados finales
fueron `0/1/0` y `0/2/0`; los de episodios consolidados fueron `55/70/60` y
`495/767/489`.

El probe separado de lifecycle ejecutó `8` generaciones, conservó lineage
cerrada y replay de checkpoint, y terminó con el último hijo vivo. Esto no es
una ejecución integrada de población, comunicación, cultura y SLM: el
simulador canónico mantiene población fija y el protocolo social-runtime se
reporta separadamente por diseño.

El artefacto reproducible es
`experiments/learning/longitudinal-population-ecology/results.json`. No se
registraron fenómenos candidatos confirmables en este primer discovery; el
registro `research/discovery/longitudinal-population-ecology-v1/candidate-phenomena.json` permanece vacío.
Los stages de `50,000` y `100,000` ticks siguen diferidos según el
preregistro hasta revisar el coste del arnés y la estabilidad de los stages
inferiores. Esto es una decisión de resource envelope, no un resultado
biológico negativo.
