# Milestone J — Desarrollo predictivo autónomo

## Estado

Diseño en implementación incremental. El codec con cero exacto, la atención
anti-captura, las hipótesis, la reparación de rutas y la predicción shadow ya
están disponibles. La promoción productiva de predictores y los estudios
longitudinales siguen sujetos a gates de evidencia y seguridad.

## Propósito

Convertir señales opacas y relaciones estadísticas en hipótesis contrastables.
La atención debe invertir recursos donde espera reducir incertidumbre, y una
regularidad solo puede consolidarse como conocimiento cuando supera una prueba
fuera de muestra. La instrumentación del Observatory es externa y nunca se
inyecta en las decisiones del organismo.

## Líneas de trabajo

### P0 — Persistencia y atención

1. **Codec de pesos con cero exacto y zona muerta.** Todo `|w| <=
   prune_threshold` se codifica como cero; los valores fuera de la zona muerta
   conservan signo tras el round-trip. El codec se versiona: checkpoints
   antiguos se decodifican con su esquema original y después se migran, nunca
   se reinterpretan con la semántica nueva. Invariantes: `decode(encode(0)) ==
   0`; un peso bajo el umbral no reaparece por encima de él; el signo se
   conserva fuera de la banda muerta.
2. **Atención anti-captura.** Sustituir `stdev / abs(mean)` por una incertidumbre
   acotada (`stdev / (abs(mean) + stdev + ε)`) y aplicar rendimiento decreciente,
   ganancia informativa esperada, novedad, recencia, coste relativo y diversidad.
   Exponer concentración y entropía de atención para detectar monopolios sin
   convertirlas en conocimiento privilegiado.

### P1 — Hipótesis y conceptos varados

3. **Ciclo de vida de hipótesis sensoriales.** Una relación pasa por
   `candidate → provisional → supported | contradicted → retired`. Registrar
   muestras de evidencia y validación, estabilidad de signo/tiempo y ganancia
   predictiva frente a baselines. Una correlación joven genera hipótesis, no
   conocimiento consolidado, y las señales permanecen opacas.
4. **Conceptos `stranded`.** Diferenciar un concepto muerto de uno muy alimentado
   pero sin salida funcional. Antes de reciclarlo, abrir una ventana acotada de
   reparación de rutas y medir utilidad funcional (mejora predictiva o de
   readout), no solo activación.

### P2 — Predicción e instrumentación

5. **Predicción en shadow mode.** Evaluar hipótesis fuera de muestra contra
   baselines cero, media y persistencia. Solo una ganancia reproducible concede
   derecho a promover un nodo `PREDICTOR`; registrar errores y retirar modelos
   contradichos. No crear predictores directamente desde una correlación.
6. **Contrato Observatory.** Publicar, como observaciones, concentración/
   entropía de atención, presión estructural, churn de relaciones, conceptos
   varados, ganancia predictiva, error de cuantización y divergencia de desarrollo.
   Estas métricas no pueden retroalimentar cognición, evaluador ni permisos de
   host.

## Límites

No se amplían `BodySchema`, `STATE` o `GATE` arbitrariamente, no se incrementan
los presupuestos de nodos/aristas y no se introducen etiquetas de plataforma,
red, descubrimiento de pares ni acciones reales.

## Orden de implementación y salida

Implementar P0 en cambios pequeños y adversariales; después P1 y finalmente P2.
Cada etapa requiere tests de contrato, migración/replay de checkpoints y estudios
con resultados positivos y negativos. El milestone termina cuando los pesos
preservan la semántica de poda, ninguna señal monopoliza sostenidamente la
atención sin ganancia, las relaciones se distinguen de hipótesis soportadas,
los conceptos varados tienen reparación o reciclaje justificado, y la promoción
a `PREDICTOR` demuestra ganancia fuera de muestra. Solo entonces podrá comenzar
Milestone K.
