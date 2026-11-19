# v2b: ajuste fino de distilroberta-base con el silver — resultado

*30 de octubre de 2026 · script `entrenar_v2b.py` · modelo en `data/modelos/v2b/` (entrenado por ti en tu CPU) · conjunto de prueba **sin usar***

## 1. Entrenamiento

- `distilroberta-base`, 9 cabezas × 4 clases por oración, lr 2e-5, lote 32, 3 épocas, 96 tokens, pérdida ponderada por clase, semilla 42. 427 pasos por época, **7.6 min por época** en CPU con 8 hilos.
- Validación interna (10 % de los profesores del silver, la misma que v2a), F1 contra el silver:

| Época | Aspecto + polaridad | Detección | Pérdida de entrenamiento |
|---|---:|---:|---:|
| 1 | 0.648 | 0.791 | 6.79 |
| 2 | 0.699 | 0.838 | 3.88 |
| **3 (elegida)** | **0.705** | **0.851** | 3.20 |

La curva se aplana (+0.006 en la época 3): **no conviene entrenar más épocas**. Contra la misma validación, v2a obtuvo 0.590.

## 2. Umbral (evaluación n.º 4 en dev)

Un solo umbral global (M2.5). El óptimo en dev es **t = 0.75, el mismo que eligió la validación del silver**, así que el resultado de dev no queda inflado por calibrar. Meseta plana entre 0.70 y 0.85 (0.617–0.623).

## 3. Resultado en dev (99 comentarios, 212 aspectos)

| | v1 | v2a | **v2b** | Etiquetador LLM (maestro) | Acuerdo humano–modelo |
|---|---:|---:|---:|---:|---:|
| F1 aspecto + polaridad | 0.511 | 0.473 | **0.623** [0.565, 0.680] | 0.693 | 0.698 |
| F1 detección | 0.667 | 0.672 | **0.759** [0.720, 0.802] | 0.779 | 0.853 |
| F1 macro (aspecto + polaridad) | 0.376 | 0.399 | **0.561** | 0.600 | |
| Exactitud de polaridad | 0.767 | 0.704 | **0.821** | 0.889 | |
| Recall / precisión de negativos | 0.44 / 0.62 | 0.64 / 0.36 | **0.68 / 0.59** | 0.84 / 0.62 | |
| Aspectos predichos (gold 212) | 187 | 291 | **244** | 276 | |

**Comparaciones pareadas** (bootstrap sobre los mismos comentarios, 2,000 remuestras):

| | Diferencia | IC 95 % | Gana en |
|---|---:|---|---:|
| v2b − v1 | **+0.112** | [+0.052, +0.170] | 100 % |
| v2b − v2a | +0.150 | [+0.090, +0.207] | 100 % |
| v2b − etiquetador LLM | −0.069 | [−0.120, −0.021] | 0 % |

Por aspecto (aspecto + polaridad; `n_gold`): ACC 0.77 (41), CAL 0.71 (66), RIG 0.66 (30), CLI 0.57 (21), CLA 0.52 (11), CAR 0.41 (20), ASI 0.32 (14), ORG 0.29 (6), RET 0.80 (3; no interpretable). Integridad: 0 evidencias que no sean subcadena exacta, 0 duplicados.

## 4. Lectura

1. **v2b es la mejor candidata entrenada** y la única que cumple lo que pide el entregable (Transformer con ajuste fino). Mejora a v1 con claridad, sobre todo en detección (0.667 → 0.759) y en negativos (recall 0.44 → 0.68).
2. **Queda 0.07 por debajo de su maestro**, que es lo esperable al destilar 4,000 comentarios en un modelo de 82 M de parámetros.
3. **Débil en CAR, ASI y ORG**: heredan la sobre-detección del silver (ASI 23 predichos contra 14) y tienen pocos casos en dev.
4. Con `F1_MIN_VISIBLE = 0.60`, en la página quedarían ocultos del top 3 los aspectos por debajo de ese umbral cuando se registren las métricas por aspecto (decisión de producto).

## 5. Evaluaciones en dev usadas: 4 de 7

v1 · etiquetador LLM (prompt v1) · v2a · v2b. Quedan 3.
