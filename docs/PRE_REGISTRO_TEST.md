# Pre-registro de la evaluación en test

*Escrito el 30 de octubre de 2026, **antes** de ejecutar cualquier evaluación en test. En ese momento `data/uso_test.log` no existía: el conjunto de prueba (300 comentarios) no se había usado nunca.*

## Decisión (opción A)

1. **Modelo elegido para el proyecto: v2b `roberta-base` con umbral t = 0.94.** Criterio: mayor F1 micro aspecto + polaridad en dev (0.650), regla de selección fijada de antemano; umbral calibrado en dev (M2.5).
2. **Esta elección no cambia por el resultado del test**, salga como salga.
3. Se evalúan también en test, **solo como información** (no para elegir):
   - v2b `distilroberta-base`, t = 0.75 (la alternativa comparada).
   - v0 (`reglas-v0.2-lexico`) y v1 (`reglas-v0.2-hf`), como líneas base del reporte.
4. Cada versión se evalúa **una sola vez** en test (`evaluar --conjunto test --confirmar-test`); los resultados se reportan tal cual, con intervalos al 95 % por bootstrap. La comparación roberta − distilroberta en test se reporta pareada.
5. Se registra en `modelo_version` **solo** el modelo elegido, con sus métricas de test.

## Identificación de lo evaluado

| Elemento | SHA-256 (primeros 16) |
|---|---|
| `data/gold_para_anotar.csv` (gold v2 con Rigor re-anotado) | `e6aed15e1dcb249e` |
| `data/modelos/v2b_roberta/modelo.pt` (`v2b-roberta-base`, `t_dev` 0.94) | `ad82ff76abb9c93b` |
| `data/modelos/v2b/modelo.pt` (`v2b-distilroberta`, `t_dev` 0.75) | `833bb5fa270f076f` |

## Cautelas declaradas de antemano

- El umbral de roberta (0.94) se eligió en dev; su F1 de dev (0.650) es optimista. Con el umbral del silver (0.75) habría quedado en 0.614.
- La ventaja de roberta sobre distilroberta en dev (+0.027) no fue significativa (IC [−0.023, +0.078]).
- Dev se usó también para el control de calidad del silver y para re-anotar Rigor; el test no se usó para nada de eso.
