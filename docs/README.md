# Documentación

Este índice separa estado normativo, diseño, decisiones y evidencia de investigación.

La política de versiones y releases está en [`VERSIONING.md`](VERSIONING.md).

## Estado y orientación

- [`roadmap.md`](roadmap.md) — **fuente canónica del estado y de la historia de milestones**.
- [`releases/v0.76.33.md`](releases/v0.76.33.md) — cierre vigente y límites de la release.
- [`../ORGANISM.md`](../ORGANISM.md) — evolución narrativa del organismo.
- [`glossary.md`](glossary.md) — vocabulario compartido.

## Arquitectura y decisiones

- [`architecture/README.md`](architecture/README.md) — límites entre paquetes y componentes.
- [`adr/`](adr/) — decisiones arquitectónicas permanentes.
- [`safety/README.md`](safety/README.md) — límites de seguridad, consentimiento y host real.

## Diseños técnicos

- [`design/`](design/) — contratos y diseños antes o durante la implementación.
- [`artificial-life-model.md`](artificial-life-model.md) — modelo funcional de analogías biológicas.
- [`math/`](math/) — formalización matemática de percepción, atención, aprendizaje y evaluación.

## Método y evidencia

- [`methodology/README.md`](methodology/README.md) — metodología general.
- [`../research/protocols/`](../research/protocols/) — protocolos definidos antes de ejecutar estudios.
- [`../research/studies/`](../research/studies/) — estudios y resultados.
- [`../research/audits/`](../research/audits/) — auditorías, hallazgos y límites de validación.
- [`../research/decisions/`](../research/decisions/) — decisiones de investigación.

Los diseños no son resultados: una hipótesis o contrato en `docs/design/` no implica que
esté implementado. Para saber qué está implementado, consultar primero `roadmap.md` y la
release correspondiente.

## Planes históricos

[`superpowers/plans/`](superpowers/plans/) contiene planes de ejecución conservados
como trazabilidad histórica. Sus casillas `pending` describen el estado del plan
cuando se escribió, no el estado canónico actual; no deben usarse para determinar
qué está implementado.
- [`design/milestone-i-fisiologia-integrada.md`](design/milestone-i-fisiologia-integrada.md) — diseño pendiente para cerrar necesidades vitales y mortales.
- [`design/milestone-j-desarrollo-predictivo.md`](design/milestone-j-desarrollo-predictivo.md) — diseño pendiente de hipótesis y predicción autónomas.
- [`design/milestone-k-sociabilidad-emergente.md`](design/milestone-k-sociabilidad-emergente.md) — diseño pendiente de sociabilidad celular emergente.
