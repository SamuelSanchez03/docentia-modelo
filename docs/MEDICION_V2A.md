# v2a: embeddings (all-MiniLM-L6-v2) + regresión logística — resultado

*30 de octubre de 2026 · script `entrenar_v2a.py` · modelo en `data/modelos/v2a/` · conjunto de prueba **sin usar***

## 1. Qué se hizo

- Entorno `ecid`: se instaló `sentence-transformers` 6.2.0 (simulación previa: no cambió torch 2.12 ni transformers 5.11). Modelo de embeddings descargado de Hugging Face (~90 MB).
- Silver: 15,259 oraciones (3,998 comentarios). **Validación interna:** 10 % de los profesores del silver (104 profesores, 419 comentarios, 1,617 oraciones), semilla 42.
- 9 regresiones logísticas multiclase (`class_weight="balanced"`), una por aspecto, sobre embeddings normalizados de 384 dimensiones.
- **Selección solo en la validación del silver:** C ∈ {0.1, 0.25, 0.5, 1.0} × umbral t ∈ {0.30…0.99}. La primera búsqueda dejó el óptimo en el borde (t = 0.90, C = 0.5); se amplió y quedó dentro: **C = 0.25, t = 0.85** (F1 aspecto + polaridad 0.590 y detección 0.778 *contra el silver*). Reentrenado con todo el silver. ~4 min en CPU.

## 2. Resultado en dev (evaluación n.º 3 de la lista cerrada: v1, etiquetador LLM, v2a)

| (dev, 99 comentarios) | v1 | **v2a** | Etiquetador LLM |
|---|---:|---:|---:|
| F1 aspecto + polaridad | 0.511 | **0.473** [0.420, 0.532] | 0.693 |
| F1 detección | 0.667 | **0.672** | 0.779 |
| Exactitud de polaridad | 0.767 | 0.704 | 0.889 |
| Recall / precisión de negativos | 0.44 / 0.62 | 0.64 / 0.36 | 0.84 / 0.62 |
| Aspectos predichos (gold: 212) | 187 | 291 | 276 |

**Pareado v2a − v1: −0.038, IC 95 % [−0.112, +0.038]** (v2a gana en el 15 % de las remuestras). No es mejor.

## 3. Por qué

1. **Sobre-detección:** 291 aspectos contra 212 del gold, sobre todo en CLA (33 contra 11), ASI (31 contra 14), CLI (30 contra 21) y RET (9 contra 3). La hereda del silver (2.93 aspectos por comentario contra 2.20 del gold) y el umbral, elegido contra el silver, no la corrige frente al gold.
2. **Un clasificador lineal sobre embeddings congelados distingue mal matices** («hard to hear» frente a «hard class», signo de Rigor). Su exactitud de polaridad (0.70) queda por debajo de v1 (0.77).
3. **El maestro pone el techo:** el etiquetador LLM que generó el silver logra 0.693 en dev; un modelo entrenado con sus etiquetas difícilmente lo supera.

## 4. Lectura para v2b

- v2a confirma que aprender del silver da detección al nivel de v1 sin reglas, pero no basta: hace falta un **encoder con ajuste fino** (v2b), que ve la oración completa y aprende el signo.
- Por la sobre-detección heredada, el umbral de v2b debería confirmarse en dev como permite M2.5 (un solo umbral global), no solo en el silver.
- Estimación de v2b en tu CPU (16 núcleos): [ESTIMACIÓN] `distilroberta-base`, 15k oraciones, 3 épocas, del orden de 40–70 min. Viable sin Colab.
