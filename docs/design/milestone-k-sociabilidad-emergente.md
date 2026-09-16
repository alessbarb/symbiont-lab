# Milestone K — Sociabilidad emergente

## Estado

Diseño en implementación incremental. Ya existe un ledger de relaciones
agregadas, persistencia de evidencia y un motor local de intercambio y
competencia sobre recursos finitos. La frontera multi-organismo ya dispone de un hábitat social explícitamente
autorizado, admisión/liberación bounded y mediación de intercambio/competencia.
Los estudios de reciprocidad y revisión relacional están cubiertos en modo
evaluator-only. El runtime ya puede ejecutar un paso social autónomo bounded a
partir de presencia opaca, memoria local y tokens de recursos autorizados; la
evidencia negativa también puede producir propuestas locales de competencia
que el hábitat adjudica por lotes. La emergencia multi-organismo prolongada y
la especialización siguen siendo gates abiertos. El estudio
`social_runtime_longitudinal` cubre ahora una trayectoria prolongada de pasos
autónomos con checkpoint intermedio y mide diversidad de pares e aislamiento;
no constituye todavía evidencia de especialización emergente. La memoria
`ResourceEvidenceLedger` permite elegir entre tokens opacos según disponibilidad
observada, revisar la elección tras una denegación y restaurar esa evidencia;
esto demuestra adaptación ecológica local, no un nicho impuesto ni una función
de recompensa social. La API de rechazo registra además evidencia direccional
de una negativa y conserva la suspensión a través de checkpoint/replay hasta
que el organismo la reanuda; rechazo y daño siguen siendo estados distintos.
Los resultados de competencia actualizan también la evidencia de disponibilidad
del recurso, de forma que una escasez observada puede cambiar la próxima
elección sin imponer una utilidad universal.
El estudio `social_runtime_specialization` demuestra una primera diferenciación
de elecciones bajo contención sintética y recursos renovables, pero no prueba
todavía estabilidad fuera de ese régimen ni una especialización general.
La proyección browser del Observatory conserva también los rechazos
direccionales del ledger. Esta paridad es observacional: no convierte el
contador en reputación ni introduce una señal de vuelta al runtime.
El `ResourceEvidenceLedger` aplica además una ventana de reexploración
bounded: una denegación antigua puede volver a contrastarse usando únicamente
los ticks y la frescura locales. La adaptación sigue siendo revisable y no se
convierte en una preferencia permanente impuesta por el evaluador.

## 1. Propósito

Proporcionar a cada Symbiont las capacidades mínimas para detectar, iniciar,
mantener, revisar y terminar interacciones con otros Symbionts dentro de un
hábitat explícitamente autorizado. El proyecto no diseña una sociedad ni define
qué relaciones son deseables.

La hipótesis es celular: una célula no recibe una política social central, sino
receptores, señales, costes, memoria y mecanismos de adhesión, separación,
cooperación y conflicto. Los Symbionts deben recibir un sustrato análogo y
construir sus propias relaciones a partir de su trayectoria.

## 2. Invariantes

- El hábitat y sus límites de recursos siguen siendo autoridad externa.
- La cognición del organismo no recibe etiquetas del evaluador como objetivos.
- No existe una recompensa universal por cooperar ni una penalización universal
  por competir.
- Ninguna relación se vuelve verdadera por consenso, similitud o una sola señal.
- Las relaciones son locales, contextuales, revisables y con caducidad de
  evidencia.
- Toda interacción está acotada por tamaño, frecuencia, coste y consentimiento.
- No se habilitan red, descubrimiento de peers, propagación, sabotaje,
  credenciales, escritura del host ni acciones reales.

## 3. Capacidades que se proporcionan

### 3.1 Percepción social

El organismo puede recibir señales acotadas de un vecino autorizado: presencia,
actividad, disponibilidad de canal, respuesta a una solicitud, resultado de un
intercambio, presión de recurso y cambios temporales. Las identidades son tokens
locales; no se exportan nombres humanos ni semántica del proveedor.

### 3.2 Reconocimiento y memoria

Cada organismo mantiene una memoria propia y limitada de interacciones: qué se
observó, cuándo, con qué calidad, qué coste tuvo, si hubo reciprocidad, si la
afirmación fue validada y qué incertidumbre permanece. La memoria puede degradar,
ser contradicha y revisarse; no es una lista permanente de reputación.

### 3.3 Intercambio

Los canales permiten anunciar, solicitar, aceptar, rechazar, validar y retirar
artefactos bounded. Compartir es una decisión del Symbiont, no una obligación del
hábitat. El receptor conserva procedencia, frescura, independencia y conflicto.

### 3.4 Asociación y separación

Un Symbiont puede repetir una interacción, cambiar su frecuencia, suspenderla,
reanudarla, abandonar una agrupación temporal o permanecer aislado. El runtime
no debe forzar emparejamientos para producir sociabilidad.

### 3.5 Competencia

La competencia aparece cuando dos organismos demandan recursos finitos o canales
incompatibles. Sus efectos son fisiológicos y ecológicos, declarados y medibles;
no son castigos morales ni decisiones del evaluador.

### 3.6 Especialización

La división de capacidades puede emerger si los costes, recursos y resultados
favorecen nichos distintos. No se asignan roles de cooperador, competidor o líder
desde fuera.

## 4. Representación de una relación

La implementación no almacenará `friend` o `enemy` como verdad global. Una
relación observada será un registro contextual con:

- sujeto y objeto opacos;
- canal y tipo de interacción;
- dirección y reciprocidad;
- evidencia y oportunidades de validación;
- coste y beneficio observados;
- frescura y caducidad;
- incertidumbre y conflictos;
- estado provisional (compatible, cooperativa, competitiva, incompatible,
  neutral o insuficiente);
- revisión monotónica del historial, sin sobrescribir evidencia contradictoria.

El estado es una inferencia del propio Symbiont y puede diferir entre organismos.
Dos Symbionts pueden cooperar en conocimiento y competir por almacenamiento al
mismo tiempo.

## 5. Dinámica mínima

```text
señal observada
  → decisión local de interactuar o no
  → intercambio o competencia acotada
  → resultado y coste
  → memoria de evidencia
  → revisión de expectativas y próxima decisión
```

No se introduce un planificador social central. La misma interacción puede ser
beneficiosa para un organismo, costosa para otro y neutral para un tercero.
`OrganismRuntime.autonomous_social_step()` materializa la primera transición
sin que el caller elija el peer, el rol, la valencia o el objetivo: el runtime
elige una oportunidad disponible según su evidencia local y un token opaco del
hábitat. La operación es opt-in por llamada, una sola interacción por paso y
bounded por `social_exchange_quantum`; no convierte al Observatory en un
controlador.
`propose_social_competition()` materializa la transición de conflicto sin
seleccionar un adversario: devuelve una solicitud local y deja la contención
simultánea al hábitat. Una propuesta aislada no recibe un objetivo social
ficticio.

## 6. Casos adversariales sintéticos

El laboratorio podrá generar, únicamente en hábitats sintéticos:

- cooperación costosa;
- oportunismo (*cheating*);
- señales inconsistentes;
- conflicto de claims;
- reciprocidad asimétrica;
- exclusión por incompatibilidad;
- competencia por escasez;
- agrupaciones temporales que se disuelven.

Estos casos sirven para medir robustez. No se convertirán en reglas que el
organismo deba ejecutar ni en acciones contra sistemas reales.

## 7. Contrato del Observatory

El aparato distinguirá explícitamente:

1. interacción observada;
2. evidencia retenida;
3. inferencia relacional del organismo;
4. consecuencia ecológica;
5. métrica del evaluador.

El Observatory no etiquetará una interacción como buena o mala para dirigir el
runtime. Solo mostrará la evidencia, la inferencia publicada y su incertidumbre.

## 8. Criterios de salida

El milestone estará implementado cuando:

1. dos Symbionts puedan percibirse e intercambiar registros dentro de un hábitat
   autorizado y acotado;
2. puedan rechazar, repetir, suspender y revisar interacciones;
3. la competencia consuma recursos reales del hábitat sin escapar sus límites;
4. exista memoria de reciprocidad, coste, frescura y conflicto;
5. aparezcan cooperación, competencia, aislamiento y explotación en estudios
   sin una política social central, incluyendo pasos autónomos del runtime;
6. el evaluador pueda medir esos resultados sin devolver sus etiquetas al runtime;
7. replay, reinicio, muerte y reproducción mantengan identidad y trazabilidad;
8. los contratos de red, persistencia, privacidad y consentimiento continúen
   cerrados.

## 9. Orden de implementación posterior

La deuda histórica del Observatory no bloquea las capacidades del núcleo: sus
proyecciones deben permanecer pasivas y se validan con contratos independientes.
El orden de cierre del milestone es:

1. completar frescura, reciprocidad y conflictos en la memoria relacional;
2. validar rechazo, repetición, suspensión y reanudación en replay;
3. ejecutar estudios adversariales de cooperación, oportunismo, aislamiento y
   competencia sin políticas sociales centrales;
4. verificar reinicio, muerte y reproducción con trazabilidad de identidad;
5. cerrar la matriz de contratos Observatory y la paridad replay/live.
