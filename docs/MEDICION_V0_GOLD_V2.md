# Medición de v0 (`reglas-v0.2-lexico`) contra el gold v2 (criterio denso)

> **Superado (30-oct-2026):** cifras con los signos de Rigor anteriores. Las vigentes están en `MEDICION_GOLD_V2_RIG.md` (v0 0.411, v1 0.511 en dev).

*29 de octubre de 2026 · 99 comentarios dev, 218 aspectos anotados · conjunto de prueba **sin usar** (no existe `data/uso_test.log`) · métricas en `metricas_dev_v2.json` · gold anotado por una sola persona, sin kappa humano–humano todavía*

## 1. Gold v2

399 de 399 anotados, sin tokens inválidos. **2.30 aspectos por comentario** (v1: 1.16) y 19 comentarios `ninguno`. Distribución: 415 `+`, 333 `-`, 171 `0`. v0 predice 1.89 por comentario en dev, así que ahora anotador y modelo tienen densidades comparables.

## 2. Resultado (dev)

| Métrica | gold v2 (denso) | gold v1 (escaso, superado) |
|---|---:|---:|
| F1 micro aspecto + polaridad (meta 0.85) | **0.360** [0.293, 0.428] | 0.300 [0.231, 0.379] |
| F1 micro solo detección | **0.667** [0.614, 0.718] | 0.527 [0.462, 0.588] |
| F1 macro (aspecto + polaridad) / (detección) | 0.268 / 0.563 | 0.236 / 0.414 |
| Exactitud de polaridad (aspectos bien detectados) | 0.541 | 0.570 |
| Recall de polaridad negativa | 0.239 (17/71) | 0.265 (13/49) |
| Aspectos predichos / anotados | 187 / 218 | 187 / 113 |

La mejora de detección es real y esperable: parte del «error» de v1 era un gold escaso. La polaridad no mejoró.

## 3. Errores (dev)

| Tipo | n (v2) | n (v1) |
|---|---:|---:|
| Aciertos (aspecto y signo) | 73 | 45 |
| Aspecto omitido (FN) | **83** | 34 |
| Signo equivocado | **62** | 34 |
| Falso positivo (FP) | 52 | 108 |

- **Signo (62):** 49 son «el gold tiene `+` o `-` y v0 predijo `0`». v0 predice `0` en 97 de 187 aspectos (52 %); el gold tiene `0` en 42 de 218 (19 %). De los 135 aspectos bien detectados, v0 deja 64 (47 %) en neutro. Por aspecto: CAL 19, RIG 15, ACC 10.
- **Omitidos (83):** 35 positivos, 26 negativos, 22 neutros. Por aspecto: CAL 24, CAR 13, ACC 12, CLA 9, CLI 9, RIG 7.
- **FP (52):** 33 con signo `0`. Por aspecto: CAL 11, RIG 10, ASI 9, CLI 8.

## 4. Lo que implica

1. **El cuello de botella es el signo.** v1 (reglas + sentimiento preentrenado) ataca exactamente esto. Su techo, con signo perfecto sobre lo que v0 ya detecta, es el F1 de detección: **≈ 0.667**. Mejora real pero no llega a 0.85.
2. **Para pasar de ~0.67 hay que mejorar la detección:** v0 omite 83 de 218 aspectos (recall de detección ≈ 0.62), sobre todo CAL, CAR y ACC. Eso es de v2 (detección aprendida), no de v1.
3. **Cifras por aspecto:** Retroalimentación (3) y Claridad (11) tienen F1 0 pero muy pocos casos; no se sacan conclusiones por aspecto con `n_gold` tan bajo.
4. **Lo que sigue sin existir:** kappa humano–humano (la doble anotación debe hacerla otra persona), tabla de 30 errores sobre este gold, y cualquier medición en test.
5. **Cuidado al iterar reglas con dev:** 99 comentarios son pocos; cada ajuste debe tener justificación general o el F1 de prueba decepcionará.
