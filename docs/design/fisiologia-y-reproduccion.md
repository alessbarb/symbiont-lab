# Fisiología, ontogenia y reproducción canónica

> **Estado canónico (2026-09-21):** este documento describe el modelo vigente
> de Living Body L1-L5. Sustituye el antiguo diseño basado en saturación
> cognitiva, `ReproductivePressure`, reserva reproductiva separada y asignación
> material dentro de `HabitatBirthAuthority`.

## Principio

La reproducción es fisiología. La cognición puede aprender las consecuencias
de crecer, madurar, envejecer o tener descendencia, pero no recibe una señal de
fertilidad, una recompensa reproductiva ni un objetivo de reproducción.

La frontera canónica es:

```text
WORLD
  -> materia / energía / daño / espacio

LIVING BODY
  -> energía
  -> integridad
  -> temperatura
  -> fatiga
  -> crecimiento
  -> edad
  -> senescencia
  -> estado vital

COGNITION
  <- señales opacas del cuerpo
```

## 1. Estado fisiológico único

`LivingBodyState` es el único propietario persistente de:

- `energy_reserve` / `max_energy`;
- `structural_integrity`;
- `temperature`;
- `fatigue`;
- `growth_progress`;
- `senescence`;
- `age_ticks`;
- `vital_state` y muerte irreversible;
- contabilidad metabólica funcional.

`MetabolicLedger`, `HomeostaticController`, `PhysiologyController` y
`OntogenyController` transforman o proyectan ese mismo estado. No poseen una
segunda verdad física.

## 2. Ontogenia constitutiva

La primera ontogenia canónica es continua y deliberadamente simple:

```text
birth -> growth -> maturity -> senescence -> death
```

`OntogenyController` no consulta:

- topología cognitiva;
- número de conceptos;
- adaptación;
- predicción;
- acciones aprendidas;
- bloqueo de crecimiento cognitivo;
- métricas del evaluador.

### Crecimiento

Mientras `growth_progress < 1`, el cuerpo puede convertir energía física en
crecimiento según los parámetros constitucionales:

```text
requested_progress = min(growth_rate_per_tick, 1 - growth_progress)
growth_cost =
    requested_progress
    * growth_energy_fraction_per_progress
    * max_energy
```

El progreso real queda limitado por energía disponible. Sin energía física no
hay crecimiento gratuito.

### Madurez

La madurez física se alcanza cuando:

```text
growth_progress == 1
```

No existe una condición cognitiva equivalente a “ser suficientemente listo”.

### Senescencia

Tras `senescence_start_ticks`, un cuerpo ya maduro acumula senescencia y
desgaste estructural constitutivo. La senescencia no es una puntuación de
rendimiento ni un juicio del laboratorio.

## 3. Readiness reproductiva

La capacidad reproductiva se deriva exclusivamente de estado corporal:

```text
alive
AND mature
AND not agonizing/dormant
AND integrity >= reproduction_min_integrity
AND senescence <= reproduction_max_senescence
AND energy_reserve >= reproduction_energy
```

donde:

```text
reproduction_energy =
    max_energy * reproduction_energy_fraction
```

Esto es fertilidad fisiológica, no motivación. El runtime no interpreta esta
condición como una orden de actuar.

## 4. Nacimiento asexual inicial

La primera reproducción materializada es asexual.

Si el cuerpo está fisiológicamente preparado y existe capacidad externa:

1. se selecciona el genoma heredable;
2. `HabitatBirthAuthority` reserva una identidad y un slot;
3. se crea un descendiente germinal;
4. la energía inicial del hijo se descuenta exactamente del progenitor.

Invariante de conservación:

```text
parent_energy_before
    == parent_energy_after + child_initial_energy
```

Si el nacimiento es denegado por capacidad, el progenitor no paga energía.

## 5. Autoridad de nacimiento

`HabitatBirthAuthority` tiene una única responsabilidad externa:

- identidad;
- linaje;
- generación;
- capacidad máxima de población.

No posee:

- energía;
- materia;
- `resource_budget`;
- `resource_units`;
- presión reproductiva;
- motivación;
- decisión conductual.

Al morir un organismo se libera únicamente su slot poblacional. El destino de
su materia corporal pertenece al modelo físico del World y no a la autoridad de
linaje.

La misma separación se aplica a `SharedHabitat`: admisión y liberación
modifican sólo la ocupación. No consumen ni devuelven el pool físico.
`consume()` reduce recursos y `renew()` representa una fuente externa
explícita.

## 6. Herencia

Cruza la línea germinal:

- genoma;
- constitución sensorial/motora heredable;
- parámetros fisiológicos constitucionales permitidos;
- identidad de linaje.

No cruza directamente:

- memoria;
- pesos cognitivos adquiridos;
- conceptos aprendidos;
- corpus privados;
- modelos privados;
- experiencia sensorimotora;
- `growth_progress`;
- senescencia adquirida.

Un hijo nace físicamente inmaduro y cognitivamente germinal.

## 7. Separación de telemetría cognitiva y ontogenia

`DevelopmentalTracker` puede seguir describiendo desarrollo cognitivo para
telemetría y análisis, pero no define madurez biológica.

La distinción canónica es:

```text
OntogenyController    -> desarrollo físico
DevelopmentalTracker  -> descripción del desarrollo cognitivo
```

Ninguno debe convertirse en alias del otro.

## 8. Población y ecología

La capacidad de carga es un límite externo. No es una recompensa ni una señal
de fitness.

Un resultado ecológico puede mostrar que ciertas constituciones dejan más
descendencia a largo plazo, pero ese resultado permanece evaluator-side. No se
inyecta una puntuación de éxito reproductivo en el organismo.

## 9. Gates L5

L5 no queda validado hasta demostrar:

1. crecimiento consume energía física;
2. sin energía no aparece crecimiento;
3. madurez no depende de cognición;
4. checkpoint/restore conserva crecimiento y senescencia;
5. senescencia depende de edad constitucional y produce desgaste;
6. readiness depende sólo del cuerpo;
7. denegación por capacidad no consume energía parental;
8. nacimiento conserva energía padre+hijo;
9. el hijo nace inmaduro y germinal;
10. capacidad poblacional nunca se excede;
11. muerte libera exactamente un slot;
12. ningún módulo canónico conserva `ReproductivePressure` ni una moneda
    reproductiva paralela.

## 10. No resuelto todavía

L5 no pretende resolver:

- elección conductual de reproducirse;
- cortejo;
- reproducción sexual;
- embarazo/embriología;
- transferencia física de masa corporal detallada;
- evolución de estrategias reproductivas.

Estas cuestiones sólo podrán añadirse sin romper los invariantes anteriores.
