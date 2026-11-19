# Medición de v0 (`reglas-v0.2-lexico`) en el conjunto de desarrollo

> **SUPERADO (25-oct-2026).** Estas cifras se midieron contra el **gold v1 (criterio escaso)**, que se archivó en `data/gold_v1_escaso/` (las métricas están en `metricas_dev_v0_sobre_gold_v1.json`). Son una cota inferior, no la calidad de v0. Hay que repetir la medición con el gold v2 (criterio denso). Se conserva como registro del análisis de errores. Ver `DOBLE_ANOTACION.md`.

*Corte: domingo 25 de octubre de 2026 · 99 comentarios dev, 113 aspectos anotados · conjunto de prueba **sin usar** (no existe `data/uso_test.log`) · métricas en `metricas_dev.json`*

## 1. Resultado

| Métrica | Valor | IC 95 % (bootstrap, 1,000) |
|---|---:|---|
| F1 micro **aspecto + polaridad** (la de la meta 0.85) | **0.300** | [0.231, 0.379] |
| F1 micro solo detección | 0.527 | [0.462, 0.588] |
| F1 macro (aspecto + polaridad) / (detección) | 0.236 / 0.414 | |
| Exactitud de polaridad (aspectos bien detectados) | 0.570 | |
| Recall de polaridad negativa | 0.265 (13/49) | |
| Aspectos predichos / anotados | 187 / 113 | |

Por aspecto (F1 aspecto+polaridad; `n_gold`): Rigor 0.40 (31), Organización 0.40 (3), Accesibilidad 0.34 (24), Clima 0.33 (10), Carga 0.30 (9), Calidad de clase 0.27 (21), Asistencia 0.08 (7), Claridad 0.00 (5), Retroalimentación 0.00 (3). Con 3 a 10 casos por aspecto, los F1 individuales son casi anecdóticos.

**Cota que importa:** v1 (reglas + sentimiento preentrenado) solo cambia el **signo**; la detección sigue siendo la de v0. Con signo perfecto, el F1 aspecto+polaridad no pasaría de la detección: **≈ 0.53**. Para llegar a 0.85 hay que mejorar la **detección**, no solo la polaridad.

## 2. Dónde están los 176 errores

| Tipo | n | Qué es |
|---|---:|---|
| Falso positivo (v0 marca un aspecto que no está en el gold) | 108 | 55 con signo `0`, 38 con `+`, 15 con `-`. Por aspecto: CAL 38, ASI 15, ACC 15, CLI 14, RIG 12, CAR 6, ORG 5 |
| Aspecto omitido (está en el gold, v0 no lo ve) | 34 | 18 son negativos, 11 positivos |
| Signo equivocado (aspecto bien detectado) | 34 | 27 son «el gold tiene `+` o `-` y v0 dejó `0`» |
| Aciertos (aspecto y signo) | 45 | |

20 comentarios dev tienen gold `ninguno`; en 9 de ellos v0 predijo algo.

## 3. Tabla de 30 errores (M3.5)

Muestra estratificada (14 falsos positivos, 8 de signo, 8 omitidos; semilla 42), leída a mano. La **causa** es una lectura mía del texto, no una verdad definitiva.

| # | Tipo | review_id | Aspecto | Gold → v0 | Causa | Detalle |
|--:|---|--:|---|---|---|---|
| 1 | FP | 18881 | CLA | — → 0 | Patrón amplio | «Syllabus is sometimes a mess» (el gold lo anotó como ORG-) |
| 2 | FP | 8517 | ASI | — → 0 | Patrón amplio | «open note quizzes, take home exams»: `quizzes` no es política de asistencia |
| 3 | FP | 12583 | CAL | — → 0 | Patrón amplio | «learn by yourself»: el verbo `learn` dispara CAL |
| 4 | FP | 19023 | ASI | — → 0 | Discrepancia con la guía | «Go to class… participate…»: la guía incluye participación en ASI |
| 5 | FP | 9401 | CAL | — → 0 | Patrón amplio | «tests have nothing to do with lecture»: habla de exámenes, la palabra `lecture` dispara CAL |
| 6 | FP | 18248 | RIG | — → 0 | Patrón amplio | «study **hard**»: no es dificultad |
| 7 | FP | 5137 | ACC | — → + | Patrón amplio | «**kind** of a demanding prof»: no es «amable» |
| 8 | FP | 19605 | ASI | — → 0 | Patrón amplio | «stuff on the quizes he never talks about» |
| 9 | FP | 8517 | CAR | — → 0 | Patrón amplio | «homework problems done for you in class» |
| 10 | FP | 10712 | CAL | — → 0 | Discrepancia con la guía | «His temper gets in the way of his teaching»: el gold lo anotó como ACC- |
| 11 | FP | 13966 | ASI | — → + | Discrepancia con la guía | «numerous amounts of **extra credit**»: la guía lista puntos extra en ASI |
| 12 | FP | 5451 | ASI | — → 0 | Patrón amplio | «(online)» como dato de la materia |
| 13 | FP | 9060 | CLI | — → - | Patrón duplicado | «she's **rude**»: `rude` está en ACC y en CLI; el gold solo ACC- |
| 14 | FP | 16173 | ACC | — → 0 | Discrepancia con la guía | «He cares about his students»: parece ACC+ y el gold no lo tiene |
| 15 | Signo | 5027 | ACC | + → 0 | Léxico incompleto | «cares about helping students» |
| 16 | Signo | 5804 | CAL | - → 0 | Sentimiento implícito | «any of the girls could do a better job of TEACHING» |
| 17 | Signo | 17287 | ACC | + → 0 | Léxico incompleto | «she does help you» |
| 18 | Signo | 1447 | RIG | - → 0 | Sentimiento implícito | «I worked extremely hard and still [got] a D»; además `hard` ahí es esfuerzo |
| 19 | Signo | 1460 | ACC | + → 0 | Léxico incompleto | «She's there to help you» |
| 20 | Signo | 8614 | ACC | - → + | Sarcasmo / condicional | «She'll be nice until you screw up…» |
| 21 | Signo | 19604 | ASI | 0 → + | Discrepancia con la guía | «there is no attendance policy»: la regla lo lee como positivo; el gold, neutro |
| 22 | Signo | 5462 | RIG | - → 0 | Sentimiento implícito | «misleadingly difficult» |
| 23 | FN | 9056 | CAL | - → — | Fuera de patrones | «so hard to understand and never stays on track» |
| 24 | FN | 12661 | CLA | - → — | Fuera de patrones | «tests were open book/note, but you had to voice your opinion» |
| 25 | FN | 19613 | CAL | - → — | Fuera de patrones | «inappropriate amount of movies for a college course» |
| 26 | FN | 3848 | CAL | - → — | Fuera de patrones | «doesn't know anything unless the text is in front of him» |
| 27 | FN | 5815 | ORG | - → — | Discrepancia con la guía | «all she did in lectures was summarize the readings»: ¿ORG o CAL? |
| 28 | FN | 19146 | ACC | + → — | Fuera de patrones | «always there to help» |
| 29 | FN | 12661 | CAL | - → — | Fuera de patrones | «trails off when he talks» (mismo comentario que #24) |
| 30 | FN | 8682 | ACC | + → — | Discrepancia con la guía | «will reply to your e-mail in less than 5 mins»: la guía lo pone en RET («tiempos de respuesta»), el gold en ACC |

### Recuento de causas (30)

| Causa | n | Qué arregla |
|---|--:|---|
| Patrón amplio o fuera de contexto (incl. `rude` duplicado) | 10 | Reglas más precisas, o detección aprendida (v2) |
| Discrepancia entre el gold y la guía | 7 | **Revisar con la segunda persona**, no con el modelo |
| Aspecto fuera de patrones (sin palabra clave) | 6 | Detección aprendida (v2); más reglas apenas ayudan |
| Léxico incompleto (`cares`, `help`) | 3 | v1 o v2 |
| Sentimiento implícito (comparativos, resultado, calificadores) | 3 | v1 o v2 |
| Sarcasmo / condicional | 1 | Límite conocido |

## 4. Lecturas y advertencias

1. **Dos tercios de los errores totales son falsos positivos.** Aquí v1 no ayuda: solo cambia el signo. Hace falta v2 o reglas más precisas.
2. **7 de 30 errores apuntan a un desacuerdo entre tu anotación y la guía** (ASI con participación, extra credit y «no attendance»; ACC con «cares»; RET vs ACC en correos). No sé quién tiene razón. Para eso existe la doble anotación: hoy sigue vacía, así que **no hay kappa** y no se puede separar «el modelo falla» de «el gold es inconsistente».
3. **No cambies etiquetas del gold mirando estos errores.** Corregir una etiqueta porque el modelo no coincide es fuga de información y vuelve optimista el F1. Si decides un criterio nuevo (por ejemplo «extra credit siempre es ASI+»), se aplica a **todos** los 399 comentarios, sin mirar las predicciones, y queda escrito en la guía de anotación.
4. **99 comentarios dev son muy pocos para afinar reglas.** Cada arreglo debe tener justificación general («`kind of` no es amable», «`study hard` no es dificultad»), no «hacer que este caso pase». Si no, las reglas se ajustan al dev y el F1 de prueba decepciona.
5. **Contexto de la cifra:** 0.30 es la primera medición real de una línea base de reglas léxicas, sin ningún ajuste. No dice nada sobre lo que alcanzará v2.
