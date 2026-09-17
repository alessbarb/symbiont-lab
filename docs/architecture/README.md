# Arquitectura del Sistema: Symbiont y Symbiont Lab

El repositorio Symbiont Lab está estructurado como un monorepo de investigación organizado en torno a dos paquetes de Python estrictamente desacoplados, con una separación epistemológica fundamental entre el **sujeto experimental** y el **aparato científico**:

1. **`symbiont`** (Sujeto Experimental):  
   El organismo autónomo de vida artificial, sustrato cognitivo recurrente, metabolismo digital, aclimatación en anfitrión y motor de simulación.
2. **`symbiont_lab`** (Aparato Científico):  
   Especificaciones experimentales, estudios de replicación, protocolos estadísticos, archivo inmutable de artefactos, CLI y panel pasivo de visualización.

---

## 1. Jerarquía Epistemológica y Dirección de la Información

```text
GROUND TRUTH (Simulador / Anfitrión Real)
       │
       ▼
EVALUATION EVENTS (Verdad exclusiva del simulador)
       │
       ├────────────────────────────────┐
       ▼                                ▼
OBSERVACIONES (Superficie sensorial)     EVALUADOR (Métricas de Lab / Simulador)
       │                                │
       ▼                                ▼
ORGANISMO (Agente / Cognición)          APARATO CIENTÍFICO (Estudios / Lab)
```

### Invariantes Estructurales Inviolables
1. **Cero Conocimiento Descendente (*Zero Downward Knowledge*):**  
   La verdad fundamental pertenece exclusivamente al simulador y al evaluador. Los componentes cognitivos (`symbiont.core`, `symbiont.cognition`) solo observan señales sintéticas u hostales opacas, memoria estadística local, reportes colectivos de pares y confianza derivada.
2. **Desacoplamiento Estructural Unidireccional:**  
   El sujeto experimental debe poder existir conceptual y estructuralmente en aislamiento absoluto del laboratorio.
   ```text
   symbiont_lab ───► symbiont        [PERMITIDO]
   symbiont     ───► symbiont_lab    [ESTRICTAMENTE PROHIBIDO - AST Enforced]
   ```
3. **Visualización Pasiva:**  
   La visualización en panel recibe métricas calculadas por el aparato de laboratorio; jamás define, calcula ni retroalimenta métricas a los organismos.

---

## 2. Mapa Arquitectónico de Documentación

| Documento | Enfoque | Alcance |
| :--- | :--- | :--- |
| **[`entidad-symbiont.md`](entidad-symbiont.md)** | **Tratado Técnico Integral del Organismo** | Especificación exhaustiva de `symbiont.core`, `symbiont.cognition`, `symbiont.host`, `symbiont.environment` y `symbiont.simulation`. Análisis profundo de código, fórmulas y ciclo de vida de ticks. |
| **[`../adr/README.md`](../adr/README.md)** | **Decisiones de Arquitectura (ADR)** | Catálogo de decisiones estructurales permanentes (ADR-0001 a ADR-0007). |
| **[`../safety/README.md`](../safety/README.md)** | **Límites de Seguridad y Consentimiento** | Restricciones operativas sobre telemetría de solo lectura y ciclo de vida supervisado del residente. |
| **[`../design/README.md`](../design/README.md)** | **Diseños de Ingeniería por Hito** | Especificaciones técnicas del desarrollo ontogenético (Hitos E al K). |
| **[`../math/README.md`](../math/README.md)** | **Compendio Matemático Formal** | Demostraciones analíticas, estabilidad de Welford, EWMA, Oja y optimización de Pareto. |
