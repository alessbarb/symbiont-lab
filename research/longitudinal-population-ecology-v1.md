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
