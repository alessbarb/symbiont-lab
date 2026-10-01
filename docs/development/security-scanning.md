# Seguridad y análisis estático

**Última comprobación local:** 2026-10-01, sobre el código de producción en
`main` (`a54df2662099c54731a23a913fb30980ad19f0ca`). Las modificaciones
documentales locales no cambian ese alcance.

## Alcance actual

Bandit se ejecuta sobre `src/` y `observatory/` con la configuración de
`pyproject.toml`:

```bash
.venv/bin/bandit -r src observatory -c pyproject.toml -q
```

Con Bandit **1.9.4**, la ejecución actual termina con código `0` y sin
hallazgos activos. `ruff check` **0.16.9** también termina limpio.

Esto significa que el resultado es limpio **dentro de la política configurada**;
no equivale a una auditoría de seguridad completa ni a la ausencia de riesgos
de diseño.

## Excepciones deliberadas

La configuración omite estas reglas:

- `B101`: `assert` usado para invariantes internas de investigación.
- `B105` y `B106`: tokens de protocolo que Bandit puede confundir con secretos.
- `B110` y `B112`: limpieza best-effort y control de errores en rutas no
  críticas.
- `B311`: `random` utilizado para simulación y experimentos reproducibles, no
  para claves, autenticación ni generación de secretos.

Estas exclusiones son una deuda de precisión de la herramienta. No deben
interpretarse como autorización para usar `random` en funciones criptográficas
ni para ocultar errores de control de flujo.

## Correcciones aplicadas

- Las cargas PyTorch nuevas usan `weights_only=True`.
- El fallback sin `weights_only` queda limitado a versiones antiguas de
  PyTorch y está marcado explícitamente con `# nosec B614`.
- Las llamadas a `subprocess` ejecutan únicamente `git rev-parse HEAD`, sin
  entrada externa ni comandos construidos dinámicamente.
- Los `# nosec` de subprocess y del fallback PyTorch están localizados en las
  líneas concretas afectadas.

## Deuda pendiente

La solución actual es una baseline operativa, no la configuración final ideal.
En una pasada posterior se debe:

1. Sustituir `assert` de invariantes críticas por excepciones explícitas.
2. Revisar individualmente los `except/pass` y `except/continue`.
3. Reducir las exclusiones globales a exclusiones por archivo o línea cuando
   el contexto esté demostrado.
4. Eliminar el fallback antiguo de PyTorch cuando deje de ser necesario
   soportar esas versiones.
5. Ejecutar Bandit junto con revisión manual de los cambios de seguridad; el
   código `0` de Bandit no sustituye esa revisión.

## Criterio para futuras correcciones

La prioridad será corregir la causa del hallazgo en el código. No se añadirán
exclusiones globales, `# nosec`, cambios de configuración ni relajaciones de
tipado solo para obtener una ejecución limpia. Solo se aceptará una excepción
cuando:

1. el hallazgo sea un falso positivo demostrado o exista una limitación
   documentada de compatibilidad;
2. la alternativa segura sea incompatible con el contrato activo o con la
   reproducibilidad científica;
3. la excepción sea lo más localizada posible; y
4. quede registrada junto con su justificación y una deuda concreta de
   retirada, si procede.

Una herramienta sin errores no se considerará evidencia suficiente si se ha
obtenido ocultando el problema.

## Evidencia relacionada

- `pip-audit` **2.10.1** terminó sin vulnerabilidades conocidas entre las
  dependencias instaladas que pudo auditar. La distribución local
  `symbiont-lab` (`0.90.0`) no está publicada en PyPI y quedó expresamente sin
  auditar; por tanto, este resultado no cubre las dependencias declaradas por
  el propio proyecto si no están instaladas o resueltas por separado.
- `pip-audit` consulta PyPI; la comprobación del 2026-10-01 se ejecutó con
  acceso a red. Un fallo de red no debe registrarse como un resultado limpio.
- La política y las excepciones están versionadas junto con el código para
  evitar que el resultado limpio pierda contexto.
