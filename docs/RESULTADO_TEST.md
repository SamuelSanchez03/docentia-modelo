# Resultado en test (evaluación única)

*30 de octubre de 2026 · 300 comentarios, 667 aspectos anotados · decisión fijada antes en `PRE_REGISTRO_TEST.md` · cada versión evaluada una sola vez (`data/uso_test.log`: 4 líneas, una por versión)*

## 1. Resultado

| Versión | Papel | F1 aspecto + polaridad | F1 detección | Exactitud de polaridad | Recall / precisión de negativos |
|---|---|---:|---:|---:|---:|
| **v2b `roberta-base` (t = 0.94)** | **Elegida** | **0.647** [0.614, 0.680] | **0.746** [0.720, 0.772] | 0.867 | 0.58 / 0.74 |
| v2b `distilroberta-base` (t = 0.75) | Informativa | 0.626 [0.595, 0.656] | 0.761 | 0.822 | 0.64 / 0.58 |
| v1 (reglas + sentimiento) | Línea base | 0.528 [0.490, 0.567] | 0.640 | 0.825 | 0.41 / 0.67 |
| v0 (reglas + léxico) | Línea base | 0.457 [0.415, 0.501] | 0.640 | 0.714 | 0.29 / 0.75 |

F1 macro (aspecto + polaridad): roberta 0.536 · distilroberta 0.548 · v1 0.434 · v0 0.393.

**Pareados en test** (2,000 remuestras, solo informativos):

| | Diferencia | IC 95 % | Gana en |
|---|---:|---|---:|
| roberta − distilroberta | +0.021 | [−0.005, +0.048] | 94 % |
| roberta − v1 | **+0.118** | [+0.080, +0.158] | 100 % |
| roberta − v0 | **+0.189** | [+0.144, +0.235] | 100 % |

## 2. Lectura

1. **El resultado de dev se sostuvo:** roberta 0.650 en dev → **0.647 en test**; distilroberta 0.623 → 0.626. El umbral 0.94, aunque elegido en dev, no estaba sobreajustado.
2. **Frente a la línea base de reglas, la mejora es clara y significativa:** +0.12 sobre v1 y +0.19 sobre v0.
3. **roberta frente a distilroberta:** +0.021, no significativo (IC cruza 0). roberta es más precisa (582 aspectos predichos contra 784; gold 667) y firma mejor; distilroberta detecta algo más.
4. **Meta original (0.85): no alcanzada.** El acuerdo humano–modelo medido con la guía es 0.698 (IC 0.62–0.77); el modelo queda a ~0.05 de ese techo. Estado: **`en_calibracion`**, con la métrica visible.

## 3. Por aspecto (roberta, test; F1 aspecto + polaridad · `n_gold`)

| Aspecto | F1 | n_gold | ¿Pasa `F1_MIN_VISIBLE = 0.60`? |
|---|---:|---:|:---:|
| Calidad de clase | 0.77 | 222 | Sí |
| Accesibilidad y trato | 0.74 | 116 | Sí |
| Clima de aula | 0.66 | 54 | Sí |
| Rigor de calificación | 0.64 | 94 | Sí |
| Claridad de evaluación | 0.56 | 45 | No |
| Organización / proyectos | 0.45 | 23 | No |
| Carga de trabajo | 0.40 | 61 | No |
| Asistencia / formato | 0.36 | 38 | No |
| Retroalimentación | 0.24 | 14 | No |

**Consecuencia para la página:** con `F1_MIN_VISIBLE = 0.60`, solo CAL, ACC, CLI y RIG podrán aparecer en el top 3 de fortalezas y oportunidades; los otros cinco seguirán visibles en el detalle con sus conteos. Es una decisión de producto que conviene confirmar.

## 4. Registro

- `data/modelo_version.csv`: fila `v2b-roberta-base`, `en_calibracion`, `f1_micro = 0.6469`, `f1_por_aspecto` con `f1_pol`, `f1_det` y `n_gold`, `n_gold = 300`.
- El SQL equivalente para Supabase está generado pero **no se ha ejecutado**.
- Pendiente: generar `data/review_aspecto_v2b_roberta_base.csv` con los 18,996 comentarios e importarlo a Supabase, con tu confirmación.
