# Type checking con Pyright

## Política

Pyright se utiliza como análisis de tipos del código de producción incluido en
`src/` y `observatory/`. Las pruebas, campañas, artefactos generados y
directorios históricos no forman parte de este alcance.

La configuración se encuentra en `pyrightconfig.json` y usa `basic` como punto
de partida. No se deben añadir exclusiones, `# pyright: ignore` ni cambios de
nivel para convertir errores reales en un resultado limpio. Una excepción solo
es válida si:

1. el diagnóstico corresponde a un falso positivo demostrado o a una
   dependencia opcional compatible con el diseño;
2. la corrección directa rompería un contrato activo, compatibilidad histórica
   explícita o reproducibilidad científica;
3. la excepción se limita al archivo o línea afectados; y
4. se documentan la razón, el alcance y la deuda de retirada.

## Alcance actual

El patrón `**/tests/**` excluye también `observatory/tests/`, no solo el
directorio raíz `tests/`. Esto evita que los contratos de prueba se mezclen con
el diagnóstico del código de producción.

Los errores restantes deben resolverse por causa raíz y agruparse por contrato:

- imports que apuntan a APIs históricas o módulos inexistentes;
- tipos opcionales que requieren una comprobación de estado real;
- argumentos incompatibles con las firmas actuales;
- tipos de persistencia, telemetría y física que necesitan modelos explícitos.

El número total de diagnósticos no se considera una métrica suficiente: cada
grupo debe validarse con pruebas enfocadas y sin relajar globalmente Pyright.
