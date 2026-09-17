# Reproducción y linaje

<a id="que-es"></a>

## Qué es

Un Symbiont puede reproducirse, pero la reproducción aquí no significa
copiar un proceso ni desplegar una instancia nueva a voluntad. Significa
crear una identidad de organismo distinta, con su propio genoma heredado y
su propio desarrollo cognitivo independiente — sujeto a autorización
explícita de hábitat y capacidad de carga, nunca como propagación
descontrolada.

<a id="mecanismo"></a>

## Mecanismo

La presión reproductiva no depende de la edad ni de tocar un límite
puntual: se activa solo si, durante varios ticks consecutivos sostenidos,
el organismo es viable, adaptativo y su capacidad fenotípica está saturada
frente a crecimiento que quedó bloqueado por falta de espacio. Solo
entonces el organismo queda `REPRODUCTIVELY_READY`.

El primer mecanismo asexual es el brote clonal (*clonal budding*): el
progenitor **no muere ni se divide**. El descendiente recibe el mismo
genoma heredable pero una identidad de organismo nueva y única, y — esto es
central — un grafo cognitivo germinal completamente vacío. No hereda pesos
sinápticos adquiridos, líneas base sensoriales, creencias ni memoria
biológica del progenitor. El genotipo se transmite; el fenotipo se
desarrolla desde cero, independientemente.

Materializar un descendiente nunca es una operación libre: `HabitatBirthAuthority`
convierte el nacimiento en una transacción atómica. Si la capacidad de
carga del hábitat está colmada, el nacimiento se deniega en bloque y la
reserva reproductiva acumulada por el progenitor se revierte intacta — no
se pierde parcialmente, no se consume por un intento fallido. Un
nacimiento exitoso consume la presión que lo justificó, para que un mismo
evento de saturación histórica no genere descendientes indefinidamente.

El linaje de organismo es una estructura separada del linaje de genoma:
dos descendientes clonales pueden compartir exactamente el mismo
`genome_id` y tener, aun así, `organism_id` distintos e historias de vida
completamente independientes.

<a id="implementado"></a>

## Qué hay implementado

- Presión reproductiva basada en saturación sostenida, no en edad —
  **[implementado]**.
- Brote clonal con fenotipo germinal vacío (sin memoria ni pesos
  heredados) — **[implementado]**.
- Autoridad de hábitat transaccional: nacimiento denegado revierte la
  reserva del progenitor íntegramente — **[implementado]**.
- Separación de linaje de organismo y linaje de genoma — **[implementado]**.
- Reproducción emparejada (recombinación de loci declarados entre dos
  progenitores compatibles) — **[parcial]**: el mecanismo de recombinación
  existe y está probado; su generalización ecológica de largo plazo se
  trata en el capítulo 7.

<a id="evidencia"></a>

## Evidencia

Está probado que la presión reproductiva requiere persistencia sostenida
antes de habilitar un brote, y que ese brote consume la presión exactamente
una vez. Está probado que un nacimiento denegado por capacidad de hábitat
llena **no** consume la presión reproductiva acumulada del progenitor —
el rechazo es atómico e íntegro. Y está probado directamente que el grafo
cognitivo base de un descendiente es una auténtica *tabula rasa*: no
transporta ningún estado adquirido del progenitor.

<a id="abierto"></a>

## Qué sigue abierto (de este mecanismo)

- La divergencia medible entre progenitor y descendiente bajo experiencias
  distintas está diseñada como propiedad esperada del sistema, pero su
  caracterización cuantitativa a largo plazo pertenece a los estudios de
  laboratorio, no a esta descripción del mecanismo.
- Los canales de herencia genética, epigenética y cultural se mantienen
  deliberadamente separados para medirse de forma independiente; su
  interacción combinada bajo presión ecológica se trata en el capítulo 7.

<a id="respaldo-formal"></a>

## Respaldo formal

Este capítulo describe una máquina de transacciones y un ciclo de vida
discreto, no un desarrollo matemático formal propio en el compendio. El
diseño normativo completo — incluyendo la recombinación de loci
heredables, la herencia epigenética acotada y la separación de canales de
inheritance — está en
[`docs/design/fisiologia-y-reproduccion.md`](../design/fisiologia-y-reproduccion.md).
