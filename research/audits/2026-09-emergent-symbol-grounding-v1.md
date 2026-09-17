# Adversarial audit — Emergent Symbol Grounding v1

## Invariantes auditados

- `v0.80.16` permanece congelado; esta línea no mueve ni reutiliza su tag.
- `symbiont` no importa `symbiont_lab`; el transporte es local y en memoria.
- El estudio no recibe IDs de significado, labels de régimen ni ground truth en la
  política. La relación latente se usa solo al calcular métricas.
- Los símbolos se construyen como identificadores opacos content-addressed; no hay
  nombres semánticos ni diccionario compartido.
- El tratamiento autónomo llama la política del organismo. Random y permuted son
  controles explícitos, no evidencia de autonomía.
- Emisión, recepción y actualización tienen costes y límites. El canal valida
  ownership y pares autorizados.
- Restore/replay compara el trace simbólico determinista; no cuenta campos
  runtime aleatorios como evidencia científica.
- Descendencia recibe ledger e historial vacíos; no se transfieren pesos, corpus ni
  significados.
- Observatory proyecta IDs, contadores y fuerza local, sin convertir asociaciones
  en etiquetas humanas ni permitir control.

## Riesgos restantes

La política actual es un baseline determinista explícito: la convergencia del
emisor proviene de una regla local seeded, no de una teoría general de negociación.
Por tanto, incluso con gates positivos, el resultado debe describirse como
convención grounded en este protocolo y no como lenguaje o semántica humana.

## Resultado ejecutado

El preregistro se ejecutó sin cambiar seeds ni criterios. ESG1–ESG10 y replay
pasaron en las tres semillas. `experiments/learning/emergent-symbol-grounding/results.json`
conserva el resultado por seed y los controles. No se detectó tabla de significado,
selección de símbolo desde el harness, ni contaminación de Private SLM. El cierre
es científico únicamente para el alcance declarado: convención simbólica opaca
grounded, útil y transmisible.
