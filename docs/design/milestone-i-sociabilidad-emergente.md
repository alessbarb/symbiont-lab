# Milestone I — Sociabilidad emergente

## Estado

Diseño definido; **no implementado**. Este documento autoriza una futura fase de
implementación, pero no añade todavía relaciones, comunicación ni autoridad nueva
al runtime.

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
   sin una política social central;
6. el evaluador pueda medir esos resultados sin devolver sus etiquetas al runtime;
7. replay, reinicio, muerte y reproducción mantengan identidad y trazabilidad;
8. los contratos de red, persistencia, privacidad y consentimiento continúen
   cerrados.

## 9. Orden de implementación posterior

La implementación queda bloqueada hasta cerrar las deudas del Observatory:

1. ingestión replay/live pura;
2. matriz ejecutable de schemas;
3. transición completa del estado de UI;
4. separación view-model/DOM;
5. equivalencia de entrypoints del residente;
6. pruebas de reinicio, compactación y paridad replay/live.

Después se implementarán, en orden, señales sociales, canales de intercambio,
memoria de interacción, competencia de recursos, revisión relacional y estudios
de emergencia.
