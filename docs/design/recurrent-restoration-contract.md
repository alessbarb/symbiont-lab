# Contrato de restauración recurrente de Symbiont

**Estado:** propuesta arquitectónica para revisión e incorporación al repositorio. **Alcance:** checkpoint actual de `CognitiveGraph` y continuación de `OrganismRuntime`. **Procedencia:** resultados de `continuity.recurrent-restoration` comunicados el 15 de septiembre de 2026 (tres semillas: 42, 123, 777) y observaciones de los dos ZIP de ejecución analizados antes.

## Decisión de contrato

Un checkpoint actual es una **continuación del organismo desde estado persistido con reinicio de la dinámica recurrente y reconstrucción discreta de parámetros**. Preserva los campos que el esquema de checkpoint exporta y restaura, pero **no promete continuación idéntica al proceso que nunca se detuvo**. La salida puede mostrar una discontinuidad inicial. Si hay aprendizaje o consolidación activa, el estado posterior puede seguir una trayectoria de pesos o topología distinta de la ejecución continua aun cuando ambos estados sean válidos.

La expresión «arranque en frío» se refiere a activaciones/buffers/trazas no persistidos. «Aproximación discreta de parámetros» se refiere a pesos guardados mediante `weight_class`. Esos dos efectos son conceptualmente distintos y deben declararse por separado. El checkpoint no equivale a una copia bit a bit del estado del proceso.

Este contrato no convierte las mediciones de un laboratorio de tres semillas en garantías universales de tiempo de estabilización, error estacionario o cambio de linaje. El rendimiento cuantitativo depende del grafo, estímulos, parámetros, punto de corte y versión del kernel. Las garantías universalmente documentables se limitan a qué estado se conserva, qué se reinicializa, cómo se reconstruyen parámetros y cuál es la identidad/procedencia de la ejecución reanudada.

## Dos modos de uso

| Uso | Qué puede esperar el operador | Qué debe observar |
|---|---|---|
| Residente: reanudar tras parada/reinicio | Persistencia de los campos declarados; arranque dinámico en frío; evolución posterior válida bajo las reglas del organismo | Nuevo `run_id`, checkpoint de origen, versión y revisión; inicio de readouts y cambios de trayectoria |
| Laboratorio: estudiar continuidad | Comparación controlada entre ejecución continua y restaurada a partir del mismo corte y estímulos futuros | Error temporal de readout, estado dinámico, deriva de parámetros, mutaciones/topología y límites de observación |

El laboratorio puede usar una copia completa en memoria para comprobar paridad exacta y aislar causas; **ese control no cambia las garantías del checkpoint residente**. Una futura opción de restauración exacta, si se implementa, debe especificarse como formato/modo diferente y demostrar que conserva todo el estado que afecta a la evolución futura.

## Frontera temporal

Un checkpoint declara un punto de corte **después de completar el tick T**. Al reanudar, el siguiente estímulo se consume en T+1. Deben registrarse el tick T, la identidad durable del organismo, el `run_id` y `sequence` del último evento confirmado si existen, revisión topológica, versión del esquema, identidad efectiva del kernel y procedencia del checkpoint. Un `run_id` nuevo identifica el flujo de transporte reanudado; `display_id` por sí solo no demuestra que dos runs sean una misma vida.

Si el formato actual no puede registrar todos esos campos, constituyen requisitos de trazabilidad de la Prioridad 4, no garantías ya implementadas. No debe inferirse el punto de corte de fechas ZIP, heartbeat o nombre del archivo. Para comparar trayectorias, ambas ramas deben recibir exactamente los mismos estímulos a partir de T+1.

## Estado conservado y estado reinicializado

La lista exacta de campos es la definida por los esquemas de checkpoint de la versión instalada y la implementación `export_checkpoint/restore`. En los ZIP previamente analizados, `cognitive_bridge` conserva grafo/topología, linajes, tiempos de algunos ciclos de vida, normalizadores, leases sensoriales y estado de seguridad; el genoma conserva parámetros de plasticidad. Los archivos no muestran activaciones, `previous_frame`, buffers de retardos ni valores dinámicos de elegibilidad por arista. Las aristas del checkpoint muestran clases de peso, no pesos exactos.

| Categoría | Contrato para el formato observado | Efecto al reanudar |
|---|---|---|
| Estructura y conocimiento exportados | Se reconstruyen conforme al esquema y validación de la versión compatible | Permanecen disponibles, sujetos a la fidelidad de sus campos |
| Pesos guardados como clases | Se reconstruyen mediante el cuantizador de la versión (`WEIGHT_CLASSES=16`, `WEIGHT_RANGE=(-2.0, 2.0)`) | Puede variar la función de transferencia incluso con topología idéntica |
| Activaciones y frame anterior | No están en los checkpoints inspeccionados | Se inicializan según el kernel (`previous_frame={}`); puede haber un salto de readout |
| Buffers de retardo | No están en los checkpoints inspeccionados | Se inicializan según el kernel; se pierde el contenido temporal anterior |
| Valores actuales de trazas de elegibilidad | No están en los checkpoints inspeccionados | Se inicializan a cero (`eligibility=0.0`) según el kernel y cambian las actualizaciones futuras si había trazas no nulas |
| Coeficiente de decaimiento de elegibilidad | Forma parte del genoma (`plasticity.eligibility_decay`) | Mantiene su valor configurado; **no debe describirse como `λ=0`** |
| Estado aleatorio, acumuladores y datos de runtime adicionales | Requieren inventario en el código vigente | No se promete paridad exacta hasta comprobar todo estado que afecta a los siguientes ticks |

La frase precisa para elegibilidad es: «**el valor de las trazas no persistidas se inicializa al restaurar (`eligibility=0.0`)**». El valor inicial procede de la implementación verificada y no debe confundirse con el coeficiente `eligibility_decay` del genoma. Tampoco se deben declarar perdidas trazas o variables de otros subsistemas sin inspeccionar sus esquemas.

## Evidencia experimental disponible

El estudio de laboratorio `continuity.recurrent-restoration` compara A (continuo), B (copia completa en memoria), C (checkpoint real) y D (restauración experimental con pesos exactos y dinámica reiniciada). La comparación B/A presenta paridad en los tres niveles evaluados. D conserva los pesos exactos para aislar el efecto de reiniciar dinámica; C añade el efecto del checkpoint discreto **si C y D reconstruyen idénticamente todos los demás campos**.

| Nivel medido, tres semillas | B frente a A | D frente a A | C frente a A |
|---|---|---|---|
| Dinámica fija, aprendizaje congelado | Divergencia reportada 0 | Máxima diferencia inicial ~0,23; umbral <10⁻⁴ alcanzado en promedio en 8,67 ticks; error final ~10⁻¹⁵ | Error residual reportado ~0,0627; no alcanza el umbral 10⁻⁴ en el horizonte evaluado |
| Plasticidad activa, topología fija | `Δw=0`, `Δq=0` reportados | Deriva residual de peso ~0,00104 atribuida al periodo de activaciones distintas | Deriva reportada de peso ~0,06255 y de elegibilidad ~0,1634 |
| Desarrollo estructural activo | Misma trayectoria y revisiones reportadas | Coincide en las primeras consolidaciones del experimento; se comunica deriva tardía en horizontes largos | Primera consolidación posterior al corte, tick 48, divergente en las tres semillas evaluadas |

La pérdida de `previous_frame` produce, en D y en los tres grafos/estímulos ensayados, un transitorio que se reduce. De ello **no se infiere que todo `CognitiveGraph` sea contractivo**. En C, el residual y la bifurcación observados son compatibles con cambios paramétricos por cuantización; la causalidad «100% pesos» requiere demostrar identidad de C y D en todo el resto del estado restaurado o realizar ablaciones adicionales.

«Tres de tres semillas difieren en la primera consolidación» es la formulación respaldada por esos datos. «La bifurcación es inevitable para cualquier checkpoint» no lo es. Con topología fija y plasticidad activa, la deriva puede persistir aunque el error de salida vuelva a disminuir: convergencia de readout y paridad de aprendizaje son propiedades separadas.

## Límites de cualquier garantía numérica

No se declara como garantía general «transitorio disipado en ≤12 ticks». La media observada de 8,67 ticks para un umbral 10⁻⁴ en tres semillas **no es una cota superior**, ni incluye todos los grafos recurrentes admisibles. Una cota válida debe declarar norma, horizonte, estados iniciales, estímulos, topologías y parámetros permitidos, y demostrar o verificar suficientemente su condición de estabilidad.

Si, para un dominio acotado, la transición con pesos fijos satisface

$$
\|F_W(x,u)-F_W(y,u)\|\le L\|x-y\|,\quad 0\le L<1,
$$

entonces dos trayectorias con **los mismos pesos y estímulos** cumplen

$$
\|x_t-y_t\|\le L^t\|x_0-y_0\|.
$$

Este razonamiento sólo aplica mientras topología y parámetros relevantes permanezcan fijos y el estado comparable incluya buffers, activaciones y cualquier otra variable recurrente. La aparición de ciclos retardados no demuestra ni refuta por sí sola la condición ($L<1$). Un ensayo empírico que alcanza un umbral no prueba la desigualdad para todos los estados.

Con pesos aproximados $\widehat W$, si además existe una perturbación por paso uniformemente acotada $\delta$ tal que

$$
\|F_W(x,u)-F_{\widehat W}(x,u)\|\le\delta,
$$

la comparación puede acotarse condicionalmente por

$$
\|x_t-y_t\|\le L^t\|x_0-y_0\|+\delta\frac{1-L^t}{1-L}.
$$

El residual de estado se limita entonces por $\delta/(1-L)$; el error de readout necesita **otra** cota de sensibilidad de la salida.

En la implementación actual (`symbiont.cognition.checkpoint`), el cuantizador usa `WEIGHT_CLASSES = 16` sobre `WEIGHT_RANGE = (-2.0, 2.0)`. La discretización asigna:

$$
\text{class\_id} = \text{round}\left(\frac{\text{clipped} - \text{low}}{\text{high} - \text{low}} \cdot (N - 1)\right) = \text{round}\left(\frac{w - (-2.0)}{4.0} \cdot 15\right)
$$

El paso uniforme entre niveles es $\Delta w = 4.0 / 15 \approx 0.266667$. El cero exacto no es un punto de la rejilla (las clases 7 y 8 corresponden respectivamente a $-0.133333$ y $+0.133333$). Por ello, cualquier peso cercano a 0 se desplaza al menos $0.133333$ en magnitud al cuantizarse.

## Compatibilidad, fallo y observabilidad

Un checkpoint debe validar versión de esquema, compatibilidad de kernel/genoma, integridad numérica, identidad de nodos/aristas y estados temporales persistidos antes de reanudar. Si falla la validación o la aplicación, debe conservar intacto el checkpoint original y emitir un fallo observable.

Los consumidores —incluido Observatory— deben poder distinguir: ejecución continua, ejecución reanudada desde checkpoint y experimento de laboratorio. Una primera salida cero al empezar un nuevo run no debe atribuirse automáticamente a lesión cognitiva: en topologías con retardos $\ge 1$ entre sentidos y readouts, la primera salida tras un arranque dinámico en frío es estructuralmente 0 mientras la señal transita por las capas latentes. La vista Self sólo puede mostrar lo que se haya incorporado al conocimiento propio del organismo; la advertencia de restauración y el origen técnico del checkpoint pertenecen a la instrumentación externa.

La telemetría mínima necesaria para la Prioridad 4 es: `organism_id`, `run_id`, `sequence`, tick y revisión del punto de corte, hash/version del checkpoint, `kernel_version`/build efectivo, modo de restauración, campos reiniciados y primer evento confirmado tras reanudar. Una captura coherente debe enlazar registry, journal, topology y checkpoint sin tratarlos como una transacción global si no hubo barrera de exportación.

## Criterio para cerrar la Prioridad 3

1. Incorporar en la documentación del repositorio el contrato de continuación aproximada/arranque dinámico en frío, señalando expresamente que no se garantiza replay exacto de salida, peso o topología.
2. Verificar en el código que C y D sólo difieren en la precisión de peso si se afirma causalidad exclusiva, y revisar los números, normas, umbrales y horizontes comunicados contra el artefacto reproducible del estudio.
3. Inventariar el estado no persistido que determina los próximos ticks y especificar sus valores iniciales al restaurar (`previous_frame={}`, `eligibility=0.0`).
4. Validar guardado/restauración en cortes con buffers ocupados, elegibilidad no nula y antes/después de consolidación. Declarar divergencia de trayectoria donde corresponda, aunque el readout se vuelva a activar.
5. Reservar la cota empírica observada y el supuesto carácter contractivo global para una demostración matemática con dominio explícito o una promesa empírica limitada y validada por separado; no incluirlos como garantía general en este contrato.
