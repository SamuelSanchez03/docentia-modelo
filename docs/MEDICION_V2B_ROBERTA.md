# v2b con roberta-base — resultado y selección para test

*30 de octubre de 2026 · `entrenar_v2b.py --base roberta-base` · modelo en `data/modelos/v2b_roberta/` (entrenado por ti; se interrumpió tras la época 1 y se reanudó) · conjunto de prueba **sin usar***

## 1. Entrenamiento

Mismo silver, hiperparámetros y validación interna que v2b (distilroberta). ~14 min por época en CPU.

| Época | Validación interna (contra el silver): aspecto + polaridad | Detección |
|---|---:|---:|
| 1 | 0.671 | 0.821 |
| 2 | 0.738 | 0.871 |
| **3 (elegida)** | **0.749** | **0.879** |

distilroberta en la misma validación: 0.705 / 0.851.

## 2. Umbral (evaluación n.º 5 en dev)

| t | 0.75 (elegido por el silver) | 0.85 | 0.90 | **0.94 (óptimo en dev)** | 0.96 |
|---|---:|---:|---:|---:|---:|
| F1 aspecto + polaridad | 0.614 | 0.635 | 0.648 | **0.650** | 0.625 |
| F1 detección | 0.772 | 0.787 | 0.782 | 0.772 | 0.741 |
| Aspectos predichos (gold 212) | 257 | 235 | 223 | 200 | 185 |

**A diferencia de distilroberta, aquí el umbral de dev (0.94) no coincide con el del silver (0.75).** El silver sobre-detecta y roberta lo imita mejor, así que contra tu gold necesita un umbral más alto. Por eso su 0.650 en dev es **optimista** (el umbral se eligió en dev). Con el umbral del silver queda en 0.614, al nivel de distilroberta (0.623).

## 3. Resultado en dev (umbral 0.94)

| | v1 | v2b distilroberta (t 0.75) | **v2b roberta (t 0.94)** | Etiquetador LLM | Acuerdo humano–modelo |
|---|---:|---:|---:|---:|---:|
| F1 aspecto + polaridad | 0.511 | 0.623 | **0.650** [0.597, 0.703] | 0.693 | 0.698 |
| F1 detección | 0.667 | 0.759 | **0.772** [0.724, 0.817] | 0.779 | 0.853 |
| F1 macro (aspecto + polaridad) | 0.376 | 0.561 | 0.561 | 0.600 | |
| Exactitud de polaridad | 0.767 | 0.821 | **0.843** | 0.889 | |
| Recall / precisión de negativos | 0.44 / 0.62 | 0.68 / 0.59 | 0.64 / **0.66** | 0.84 / 0.62 | |
| Aspectos predichos (gold 212) | 187 | 244 | **200** | 276 | |

Pareados (2,000 remuestras): **roberta − distilroberta +0.027, IC [−0.023, +0.078]** (gana en 86 %; no significativo) · roberta − v1 +0.139 [+0.071, +0.205] · roberta − etiquetador LLM −0.042 [−0.094, +0.009].

Por aspecto (roberta / distilroberta): CAL 0.79 / 0.71 · ACC 0.77 / 0.77 · RIG 0.72 / 0.66 · ASI 0.51 / 0.32 · CLI 0.43 / 0.57 · CAR 0.39 / 0.41 · ORG 0.36 / 0.29 · CLA 0.27 / 0.52 · RET 0.80 / 0.80 (n = 3). Integridad: 0 evidencias que no sean subcadena exacta, 0 duplicados.

## 4. Selección para test

Regla pre-registrada: **se publica la candidata con mayor F1 aspecto + polaridad en dev**, con el umbral calibrado en dev (M2.5). Esa es **v2b roberta-base con t = 0.94** (0.650 contra 0.623).

Cautelas que se declaran con el resultado:
- La ventaja sobre distilroberta **no es significativa** y depende de calibrar el umbral en dev; con el umbral del silver serían equivalentes.
- Hay una meseta entre 0.85 y 0.94 (0.635–0.650); el máximo exacto es ruidoso con 99 comentarios.
- El test (300 comentarios) se usa **una sola vez**; su resultado se reporta tal cual.

Evaluaciones en dev usadas: **5 de 7** (v1, etiquetador LLM, v2a, v2b distilroberta, v2b roberta).
