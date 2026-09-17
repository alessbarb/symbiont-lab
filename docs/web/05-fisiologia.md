# Fisiología

<a id="que-es"></a>

## Qué es

Un Symbiont tiene una economía interna explícita: gasta recursos
computacionales finitos en observar, pensar, recordar y mantenerse, y esa
presión de recursos determina si el organismo está activo, estresado,
dormido o muerto. No es una metáfora — es una contabilidad real que decide
qué hace el organismo cuando los recursos escasean.

<a id="mecanismo"></a>

## Mecanismo

`MetabolicLedger` gestiona cuatro reservas finitas: observación (leer
sensores), cognición (activar y aprender el grafo), persistencia (asimilar
y consolidar memoria) y mantenimiento (gasto basal continuo). La presión
fisiológica se calcula como el ratio mínimo entre reserva y capacidad de
las cuatro: por encima de 0.5 es `NORMAL`, entre 0.2 y 0.5 `ELEVATED`, por
debajo de 0.2 `SEVERE`, y negativo `UNRECOVERABLE`.

`HomeostaticController` traduce esa presión en comportamiento: presión
elevada reduce la escala de actividad; presión severa la reduce más y
además **deshabilita la plasticidad cognitiva** — el organismo deja de
aprender cuando está bajo estrés fuerte, no solo de moverse más despacio.
Presión irrecuperable o integridad muy baja activa un modo seguro con
actividad mínima y plasticidad bloqueada. La reparación de integridad
consume recursos de mantenimiento incluso cuando no hay nada que reparar
— reparar sobre un cuerpo ya intacto igual cuesta, para que el organismo
tenga que aprender la pertinencia contextual de pedir reparación, no
recibirla gratis por defecto.

Los estados vitales forman una máquina de transición estricta:
`ACTIVE → STRESSED → DORMANT/AGONIZING → DEAD`. La muerte es terminal e
irreversible: si el runtime intenta ejecutar un tick después de la muerte,
lanza un error explícito en vez de simular continuidad. En el momento de
morir, el runtime libera atómicamente y una sola vez la asignación en el
hábitat ecológico compartido, el cupo de membresía social y el registro de
defunción en la autoridad de linaje — sin dejar asignaciones huérfanas ni
liberar dos veces.

El estado retenido de bajo valor sigue un ciclo de degradación explícito:
activo, envejeciendo, residuo, y finalmente excretado — purgado
definitivamente de la memoria, incrementando solo un contador agregado.
Nada de lo excretado se mueve a un archivo sin límite; se pierde de verdad.

<a id="implementado"></a>

## Qué hay implementado

- Contabilidad metabólica de cuatro recursos con presión derivada del ratio
  mínimo — **[implementado]**.
- Homeostasis que reduce actividad y pausa plasticidad bajo presión —
  **[implementado]**.
- Reparación acotada que cuesta recurso incluso sin beneficio en cuerpo
  intacto — **[implementado]**.
- Muerte terminal e irreversible con liberación atómica exactamente una
  vez de hábitat ecológico, hábitat social y linaje — **[implementado]**.
- Degradación y excreción irreversible de estado de bajo valor —
  **[implementado]**.

<a id="evidencia"></a>

## Evidencia

Está probado que una presión irrecuperable causa muerte irreversible, y
que el runtime rechaza ejecutar cualquier tick posterior a la muerte. Está
probado que la presión fisiológica reduce la escala de actividad y pausa
la plasticidad simultáneamente, no una sin la otra. Está probado que
intentar reparar un cuerpo ya intacto consume el recurso de esfuerzo sin
producir ninguna reparación real — el coste no es gratuito ni condicional
al resultado. Y está probado que el estado retenido efectivamente envejece
y termina excretado, no acumulado indefinidamente.

<a id="abierto"></a>

## Qué sigue abierto (de este mecanismo)

- El estudio longitudinal integrado de fisiología (reparación, reproducción
  acotada y continuidad social en una sola ejecución reproducible) es
  evaluator-only: existe como arnés determinista externo, no como una
  propiedad que el organismo observe o persiga por sí mismo.
- Los umbrales exactos de presión (0.5 / 0.2) y los factores de reducción
  de actividad (90% / 75% / 10%) son parámetros de ingeniería, no derivados
  de una teoría formal de homeostasis óptima.

<a id="respaldo-formal"></a>

## Respaldo formal

Este capítulo describe mecanismos de contabilidad e ingeniería de control,
no un desarrollo matemático formal propio en el compendio. El automodelo de
coste y salud del organismo — con el que la fisiología comparte la lógica
de EWMA y cuantización — está en
[`docs/math/08-automodelo-y-sensores-adaptativos.md`](../math/08-automodelo-y-sensores-adaptativos.md).
