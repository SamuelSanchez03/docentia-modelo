---
license: apache-2.0
language:
  - en
pipeline_tag: text-classification
base_model:
  - FacebookAI/roberta-base
  - distilbert/distilroberta-base
tags:
  - absa
  - aspect-based-sentiment-analysis
  - education
  - teaching-evaluation
  - pytorch
metrics:
  - f1
inference: false
---

# DocentIA ABSA · aspectos y polaridad en reseñas de profesores

**TL;DR (en):** sentence-level aspect-based sentiment model, fine-tuned from `roberta-base` (and `distilroberta-base`) on English student reviews of professors. For each sentence it scores 9 teaching aspects and a polarity (positive / negative / mixed-neutral). F1 (aspect + polarity) is **0.647** on 300 hand-annotated test comments, close to the ~0.70 agreement ceiling between annotators. It is **not** a drop-in `transformers` checkpoint: it needs the `ABSA` class from the [code repository](https://github.com/SamuelSanchez03/docentia-modelo).

Modelo que lee un comentario de un alumno y dice **de qué aspectos habla** y **si lo dice bien, mal o sin juicio**. Se entrenó para el proyecto DocentIA, que arma fortalezas y áreas de oportunidad de cada profesor a partir de sus evaluaciones. Su estado registrado es `en_calibracion`, con la métrica visible: no alcanza la meta original (0.85), que resultó superior al acuerdo entre anotadores.

## Versiones

| Carpeta | Base | Umbral `t` | `modelo.pt` | SHA-256 (primeros 16) |
|---|---|---:|---:|---|
| `v2b_roberta/` (**recomendada**) | `roberta-base` | 0.94 | 499 MB | `ad82ff76abb9c93b` |
| `v2b/` | `distilroberta-base` | 0.75 | 329 MB | `833bb5fa270f076f` |

Cada carpeta trae `modelo.pt` (el `state_dict` de la clase `ABSA`), `config.json` y `tokenizer/`. Los hashes son los mismos que quedaron fijados antes de evaluar en test.

## Qué hace

- **Entrada:** una oración en inglés, con el nombre del profesor enmascarado como `[PROF]`.
- **Salida:** probabilidades de 9 aspectos × 4 clases. Orden de las clases: `0` no menciona, `1` positivo (`+`), `2` negativo (`-`), `3` mixto/neutro (`0`).
- **Aspectos:** `RET` Retroalimentación · `CLA` Claridad de evaluación · `CAL` Calidad de clase · `ACC` Accesibilidad y trato · `CAR` Carga de trabajo · `RIG` Rigor de calificación · `ORG` Organización / proyectos · `CLI` Clima de aula · `ASI` Asistencia / formato.
- **Decisión:** un aspecto está presente en una oración si `1 − P(no menciona) > t`; su polaridad es el argmax de las clases 1 a 3. Por comentario, si un aspecto sale con signos opuestos en distintas oraciones queda `0`; si solo hay positivas o solo negativas gana ese signo.
- **Arquitectura:** el encoder base, `dropout` 0.1 y una capa lineal de `hidden_size → 9 × 4` sobre el primer token. Longitud máxima de 96 tokens.

## Cómo usarlo

Los pesos solos no bastan: la clase `ABSA` y el preprocesamiento (partir en oraciones y enmascarar nombres) están en el repositorio de código.

```bash
git clone https://github.com/SamuelSanchez03/docentia-modelo.git
cd docentia-modelo
pip install -r requirements.txt
python pesos_hf.py bajar SamSanchez03/docentia-absa --version v2b_roberta
```

```python
import sys
from pathlib import Path

RAIZ = Path(".")                       # raíz del repositorio de código
sys.path.insert(0, str(RAIZ))
from entrenar_v2b import _cargar, _probs

model, tok, cfg = _cargar(RAIZ / "data/modelos/v2b_roberta")
P = _probs(model, tok, ["The lectures were clear but the exams were brutal."], cfg["maxlen"])
# P["CAL"] -> matriz (n_oraciones, 4); un aspecto está presente si 1 - P[aspecto][:, 0] > cfg["t_dev"]
```

La primera vez, `_cargar` descarga el `roberta-base` de Hugging Face (unos 500 MB) para armar la arquitectura y luego carga encima `modelo.pt`. `transformers` imprime una tabla de claves `MISSING` / `UNEXPECTED` (pooler, lm_head): es normal.

## Entrenamiento

- **Datos de entrenamiento (silver):** 3,998 comentarios de profesores de entrenamiento, 15,259 oraciones, etiquetadas por oración por Claude (`sonnet`) con la guía de anotación del proyecto. Antes de usarlas se midieron contra el gold de dev: F1 aspecto + polaridad 0.693 y detección 0.779.
- **Partición:** el 15 % de los profesores se reservó antes de entrenar y nada de ellos entra al entrenamiento. La validación interna usa el 10 % de los profesores del silver (13,642 oraciones de entrenamiento y 1,617 de validación).
- **Hiperparámetros:** lr 2e-5, lote 32, 3 épocas, pérdida ponderada por clase, semilla 42, torch 2.12.0, en CPU (unos 14 min por época con `roberta-base`).
- **Umbral:** un solo `t` global, calibrado en dev (0.94 para roberta).

## Evaluación

300 comentarios anotados a mano (667 menciones de aspecto) de profesores que el modelo nunca vio. Se evaluó **una sola vez por versión**, y el modelo y el umbral se fijaron por escrito antes de mirar el test. Intervalos al 95 % por bootstrap.

| Versión | F1 aspecto + polaridad | F1 detección | Exactitud de polaridad |
|---|---:|---:|---:|
| **`v2b-roberta-base`** | **0.647** [0.614, 0.680] | 0.746 | 0.867 |
| `v2b-distilroberta-base` | 0.626 [0.595, 0.656] | 0.761 | 0.822 |
| Reglas + sentimiento preentrenado (línea base) | 0.528 [0.490, 0.567] | 0.640 | 0.825 |
| Reglas (línea base) | 0.457 [0.415, 0.501] | 0.640 | 0.714 |
| Acuerdo humano–modelo entre anotadores (techo) | ≈ 0.70 [0.62, 0.77] | ≈ 0.85 | |

`roberta-base` supera a las reglas de forma significativa (+0.118 sobre las reglas con sentimiento, +0.189 sobre las reglas solas, ambos con IC que no cruza 0). Frente a `distilroberta-base` la diferencia (+0.021) no es significativa. El F1 de dev (0.650) se sostuvo en test, así que el umbral no estaba inflado.

**Por aspecto** (`v2b-roberta-base`, F1 aspecto + polaridad en test, y menciones en el gold):

| Aspecto | F1 | Menciones |
|---|---:|---:|
| Calidad de clase | 0.77 | 222 |
| Accesibilidad y trato | 0.74 | 116 |
| Clima de aula | 0.66 | 54 |
| Rigor de calificación | 0.64 | 94 |
| Claridad de evaluación | 0.56 | 45 |
| Organización / proyectos | 0.45 | 23 |
| Carga de trabajo | 0.40 | 61 |
| Asistencia / formato | 0.36 | 38 |
| Retroalimentación | 0.24 | 14 |

## Usos previstos y fuera de alcance

- **Previsto:** análisis agregado de qué aspectos mencionan los alumnos y con qué polaridad, como apoyo a la retroalimentación docente, y como línea base para investigación.
- **No previsto:** decidir sobre una persona (contratación, sanciones, evaluación laboral) a partir de este modelo. Tampoco está validado para otros idiomas, otros tipos de texto ni otras instituciones.

## Limitaciones y sesgos

- **El gold lo anotó una sola persona.** El segundo anotador (50 comentarios) fue Claude, así que el «techo» es un acuerdo humano–modelo (kappa 0.721), probablemente optimista frente a dos humanos. El acuerdo es más bajo en Rigor (kappa 0.592).
- **Las etiquetas de entrenamiento las generó un LLM.** El modelo hereda sus errores y sesgos, y se aproxima a un criterio de anotación, no a una verdad externa.
- **Aspectos débiles.** Retroalimentación, Asistencia, Carga, Organización y Claridad de evaluación quedan por debajo de 0.60 de F1, algunos con muy pocos casos. El F1 global promedia nueve aspectos muy distintos.
- **Se pierden menciones negativas.** En test el modelo recupera el 58 % de las menciones negativas (precisión 0.74).
- **Rigor.** Por regla, la dificultad por sí sola es neutra (`RIG0`): solo es negativa si el texto la califica como injusta o arbitraria, y positiva si la califica como justa o valiosa. Esto busca no castigar a los docentes exigentes.
- **Dominio.** Reseñas en inglés de Rate My Professors, no de la institución para la que se diseñó el sistema. Puede degradarse en otros contextos.
- **Sin datos demográficos.** No se usaron nombre, materia ni columnas demográficas como entrada. Tampoco hay medición de desempeño por grupos demográficos.
- **Personas reales.** Los comentarios hablan de personas identificables; el modelo enmascara nombres antes de predecir, pero las reseñas originales no son anónimas para quien las conozca.

## Datos

Muestra de 20,000 reseñas (19,971 tras la limpieza; 18,996 con texto), en inglés, del dataset «Big Data Set from RateMyProfessor.com for Professors' Teaching Evaluation» de Jibo He (Mendeley Data, versión 2, 2020), publicado con licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/):

> He, J. (2020). *Big Data Set from RateMyProfessor.com for Professors' Teaching Evaluation* (Versión 2) [Conjunto de datos]. Mendeley Data. https://doi.org/10.17632/fvtfjyvw7d.2

Según la ficha del dataset, las reseñas se obtuvieron por rastreo web de RateMyProfessor.com entre abril y julio de 2018. **Cambios:** se eliminaron las columnas demográficas y los duplicados, se normalizaron algunos campos y se añadieron anotaciones (gold y silver). El código, las anotaciones y las métricas están en el [repositorio de código](https://github.com/SamuelSanchez03/docentia-modelo).

## Créditos

Claude (Anthropic) asistió en el desarrollo del código y en la evaluación del modelo. También se usó como anotador automático: etiquetó el silver y fue el segundo anotador de 50 comentarios del gold. El gold de 399 comentarios lo anotó a mano el autor.

## Licencia

Los pesos se publican bajo **Apache-2.0**. Son una versión modificada (ajuste fino) de `roberta-base` (licencia MIT) y de `distilroberta-base` (licencia Apache-2.0), y se entrenaron con reseñas publicadas bajo CC BY 4.0 (ver Datos). El código del repositorio de código está bajo MIT; los datos y las anotaciones, bajo CC BY 4.0.
