# DocentIA · módulo de IA (ABSA de reseñas de profesores)

Modelo que lee un comentario de un alumno y dice **de qué aspectos habla** y **si lo dice bien, mal o sin juicio**.
Este repositorio guarda todo lo del modelo: código, datos, etiquetas (gold y silver), métricas, documentación y el SQL de Supabase.
Los **pesos** (`*.pt`) no están aquí porque GitHub no admite archivos de más de 100 MB: viven en Hugging Face (ver [Pesos](#pesos)).

## Qué hace

- 9 aspectos: Retroalimentación (`RET`), Claridad de evaluación (`CLA`), Calidad de clase (`CAL`), Accesibilidad y trato (`ACC`), Carga de trabajo (`CAR`), Rigor de calificación (`RIG`), Organización / proyectos (`ORG`), Clima de aula (`CLI`) y Asistencia / formato (`ASI`).
- Por cada aspecto: positivo, negativo o mixto/neutro. La predicción se hace por oración y se consolida por comentario con un umbral global.
- Datos: Rate My Professors, 19,971 evaluaciones (18,996 con texto). Gold anotado a mano: 399 comentarios (99 dev, 300 test).

### Resultado (test, 300 comentarios, una sola evaluación)

| Versión | F1 aspecto + polaridad | F1 detección |
|---|---:|---:|
| **`v2b-roberta-base` (elegida)** | **0.647** [0.614, 0.680] | 0.746 |
| `v2b-distilroberta-base` | 0.626 | 0.761 |
| v1: reglas + sentimiento preentrenado | 0.528 | 0.640 |
| v0: reglas | 0.457 | 0.640 |
| Acuerdo entre anotadores (techo realista) | ~0.70 | ~0.85 |

La meta original (0.85) no se alcanzó: el acuerdo humano–modelo medido con la guía de anotación es 0.698, y el modelo queda a ~0.05 de ese techo. Por eso el estado registrado es `en_calibracion`, con la métrica visible. El detalle está en [`docs/RESULTADO_TEST.md`](docs/RESULTADO_TEST.md).

El modelo mejora a las reglas de forma significativa en comparaciones pareadas sobre los mismos 300 comentarios (roberta − v1: +0.118, IC 95 % [+0.080, +0.158]; roberta − v0: +0.189 [+0.144, +0.235]); frente a distilroberta, +0.021 no es significativo. El resultado de dev (0.650) se sostuvo en test (0.647), así que el umbral elegido en dev no estaba inflado. Cuando el modelo encuentra un aspecto, acierta el signo el 87 % de las veces (exactitud de polaridad 0.867).

Por aspecto (F1 aspecto + polaridad en test): Calidad de clase 0.77, Accesibilidad y trato 0.74, Clima de aula 0.66, Rigor de calificación 0.64, Claridad de evaluación 0.56, Organización 0.45, Carga de trabajo 0.40, Asistencia / formato 0.36 y Retroalimentación 0.24. Los cinco últimos quedan por debajo de 0.60 y conviene leerlos con cautela; algunos tienen pocos casos (14 menciones de Retroalimentación en el gold de test).

Cómo se construyó, los criterios de anotación y los límites de estas cifras están en [Metodología](#metodología).

## Estructura

```text
absa_baseline.py        v0/v1: reglas + léxico; también partición, muestra de gold, evaluación y kappa
entrenar_v2a.py         v2a: embeddings fijos + regresión logística (no mejoró a v1)
entrenar_v2b.py         v2b: ajuste fino de distilroberta-base / roberta-base (el modelo elegido)
generar_silver.py       etiquetas automáticas (silver) con Claude, 4,000 comentarios de entrenamiento
anotar_gold.py          herramienta local para anotar el gold a mano
validar_review_aspecto.py, separar_tablas.py   validación de predicciones y tablas relacionales para Supabase
pesos_hf.py             sube / baja los pesos a Hugging Face
MODEL_CARD.md           tarjeta del modelo; se sube a Hugging Face como su README
requirements.txt, environment.yml              dependencias (pip / conda)
data/                   reseñas, profesores, gold, silver, predicciones y logs
data/modelos/<versión>/ config.json, tokenizer/ y predicciones; aquí se bajan los pesos (modelo.pt)
silver/prompt_v1.md     prompt del silver (no renombrar: el nombre y el hash del archivo identifican el silver)
metricas/               métricas de dev y test de cada versión (metricas_*.json)
sql/                    esquema (supabase_setup.sql), vistas de agregados y sql/subida/ (carga de predicciones a Supabase)
docs/                   solo resultados de pruebas (MEDICION_*, RESULTADO_TEST, PRE_REGISTRO_TEST, PILOTO_SILVER, DOBLE_ANOTACION*) y la guía README_ejecucion.md
archivo/                absa_baseline_v0.1.py, el script original de reglas; solo de referencia
```

Los scripts se quedan en la raíz y se ejecutan desde ahí: leen y escriben rutas relativas (`data/...`) y los comandos de `docs/` los llaman así.

El frontend real (Profesor, Directivo, Coordinador) está en otro repositorio: [SamuelSanchez03/docentia-frontend](https://github.com/SamuelSanchez03/docentia-frontend). No está incluido aquí.

## Instalación

El modelo se entrenó y evaluó en un entorno conda llamado `ecid` con **Python 3.11**. Las versiones exactas están en `requirements.txt` (pip) y `environment.yml` (conda, que reutiliza el anterior). Basta con una de las dos opciones; los comandos se corren desde la raíz del repo.

### Con conda

```bash
conda env create -f environment.yml
conda activate docentia
```

Si ya tienes un entorno `docentia` y no quieres tocarlo, crea este con otro nombre: `conda env create -f environment.yml -n [nombre_env]`. Para ponerte al día en uno existente: `conda env update -n docentia -f environment.yml`.

### Con venv de Python

Hace falta un Python 3.11 (el que se usó). Si tu `python3` es otra versión, instala la 3.11 o usa la opción de conda.

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Comprobar que quedó bien

```bash
python -c "import torch, transformers, pandas; print(torch.__version__, transformers.__version__, pandas.__version__)"
```

Debe imprimir `2.12.0 5.11.0 3.0.1` (torch puede añadir un sufijo como `+cu130`).

Notas:

- **torch:** en Linux, pip instala por defecto la build con CUDA, que pesa varios GB. Sin GPU NVIDIA puedes instalar antes la build de CPU con `pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu` y luego `pip install -r requirements.txt`. El entrenamiento original se hizo en CPU.
- **`generar_silver.py`** llama a la CLI `claude` (Claude Code) con `claude -p`, que no se instala con pip. Solo hace falta para regenerar el silver; el modelo ya entrenado no la usa.

## Pesos

Hay dos modelos entrenados; el elegido es `v2b_roberta`.

| Carpeta | Base | `modelo.pt` |
|---|---|---:|
| `data/modelos/v2b_roberta/` | `roberta-base` (elegido, umbral `t_dev` = 0.94) | 476 MB |
| `data/modelos/v2b/` | `distilroberta-base` | 314 MB |

Cada `modelo.pt` es el `state_dict` de la clase `ABSA` de `entrenar_v2b.py`. El `checkpoint.pt` de 1.4 GB que tenía el entrenamiento de roberta solo guardaba el optimizador para reanudarlo y no se publica.

```bash
# bajar los pesos (deja data/modelos/v2b_roberta/modelo.pt y data/modelos/v2b/modelo.pt)
python pesos_hf.py bajar SamSanchez03/docentia-absa
python pesos_hf.py bajar SamSanchez03/docentia-absa --version v2b_roberta     # solo el elegido

# subirlos (solo quien tenga los .pt y un token de escritura de Hugging Face)
python pesos_hf.py subir SamSanchez03/docentia-absa                # repo privado
python pesos_hf.py subir SamSanchez03/docentia-absa --publico
```

El repo de pesos en Hugging Face es [`SamSanchez03/docentia-absa`](https://huggingface.co/SamSanchez03/docentia-absa). Su tarjeta, [`MODEL_CARD.md`](MODEL_CARD.md), se sube como el README de ese repo:

```bash
hf upload SamSanchez03/docentia-absa MODEL_CARD.md README.md
```

## Predecir

Con los pesos en su carpeta y desde la raíz del repo:

```bash
python entrenar_v2b.py predecir --conjunto dev  --dir data/modelos/v2b_roberta   # -> data/modelos/v2b_roberta/review_aspecto_v2b_dev.csv
python entrenar_v2b.py predecir --conjunto todos --dir data/modelos/v2b_roberta  # -> data/review_aspecto_<versión>.csv
```

El umbral sale de `config.json` (`t_dev`), salvo que pases `--umbral`.

## Reproducir el entrenamiento y la evaluación

El orden completo de comandos está en [`docs/README_ejecucion.md`](docs/README_ejecucion.md). En resumen: partición de profesores reservados → muestra de gold → anotación → silver → entrenar → calibrar el umbral en dev → evaluar en test.

```bash
python entrenar_v2b.py entrenar --base roberta-base --dir data/modelos/v2b_roberta
python entrenar_v2b.py calibrar --dir data/modelos/v2b_roberta
```

**El test se evalúa una sola vez.** El modelo elegido quedó fijado antes de mirarlo ([`docs/PRE_REGISTRO_TEST.md`](docs/PRE_REGISTRO_TEST.md), con los SHA-256 del gold y de los pesos evaluados), cada versión se evaluó una sola vez (`data/uso_test.log`) y el resultado está en [`docs/RESULTADO_TEST.md`](docs/RESULTADO_TEST.md). Para seguir iterando, usa dev.

## Usarlo desde otro proyecto

**Como submódulo** (recomendado: queda fijado a un commit):

```bash
git submodule add https://github.com/SamuelSanchez03/docentia-modelo.git vendor/docentia-modelo
cd vendor/docentia-modelo && pip install -r requirements.txt && python pesos_hf.py bajar SamSanchez03/docentia-absa
```

**Desde Python**, el esquema es este (las firmas están en `entrenar_v2b.py`):

```python
import sys
from pathlib import Path

RAIZ = Path("vendor/docentia-modelo")
sys.path.insert(0, str(RAIZ))
from entrenar_v2b import _cargar, _probs

model, tok, cfg = _cargar(RAIZ / "data/modelos/v2b_roberta")
P = _probs(model, tok, ["The lectures were clear but the exams were brutal."], cfg["maxlen"])
# P["CAL"] -> matriz (n_oraciones, 4). Columnas: 0 = no menciona, 1 = positivo (+), 2 = negativo (-), 3 = mixto/neutro (0).
# Un aspecto está presente en una oración si 1 - P[aspecto][:, 0] > cfg["t_dev"] (0.94 en roberta);
# la polaridad es el argmax de las columnas 1-3. _consolidar (entrenar_v2a.py) lo junta por comentario.
```

`_cargar` arma la arquitectura con el `roberta-base` de Hugging Face (unos 500 MB; lo descarga la primera vez si no está en la caché) y le carga encima los pesos de `modelo.pt`. Mientras lo hace, `transformers` imprime una tabla de claves `MISSING` / `UNEXPECTED` (pooler, lm_head): es normal.

Dos cosas que el pipeline original hace antes de predecir y que conviene respetar:

1. Parte el comentario en oraciones con `absa_baseline.frases`.
2. Enmascara el nombre del profesor (`absa_baseline.crear_mascara`), para que cambiar el nombre no cambie la predicción (prueba M3.4).

Los scripts leen y escriben rutas relativas (`data/...`), así que ejecútalos desde la raíz del repo.

## Metodología

### Cómo se construyó

1. **Línea base de reglas (v0).** Patrones de palabras por aspecto y un léxico de sentimiento (`absa_baseline.py`). El script original se perdió y se reconstruyó; `etiquetar` reproduce byte a byte el `data/review_aspecto.csv` que ya estaba cargado.
2. **Partición por profesor y gold.** Se reserva el 15 % de los profesores (semilla 42) y nada de ellos entra al entrenamiento. De esos profesores salen 399 comentarios anotados a mano: 99 de dev, para iterar, y 300 de test, que se usan una sola vez.
3. **Reglas + sentimiento preentrenado (v1).** La misma detección por reglas; el signo lo da un modelo de sentimiento (RoBERTa de Twitter). Mejora el signo, pero la detección tiene un techo de ~0.67.
4. **Silver.** Claude (`sonnet`, con `claude -p`) etiquetó unos 4,000 comentarios de profesores de entrenamiento (3,998 en el silver final, 15,259 oraciones), oración por oración y con la misma guía de anotación (`silver/prompt_v1.md`). Antes de usarlo se midió contra el gold de dev: F1 aspecto + polaridad 0.693 y detección 0.779, al nivel del acuerdo entre anotadores.
5. **Entrenamiento (v2).** v2a (embeddings `all-MiniLM-L6-v2` + regresión logística) no mejoró a v1. v2b ajusta un Transformer con 9 cabezas × 4 clases por oración (lr 2e-5, lote 32, 3 épocas, 96 tokens, pérdida ponderada por clase, semilla 42, validación interna con el 10 % de los profesores del silver). `distilroberta-base` llega a 0.623 en dev y `roberta-base` a 0.650, que es el elegido.
6. **Umbral y consolidación.** Un aspecto está presente en una oración si 1 − P(no menciona) supera un umbral global `t`, calibrado en dev (0.94 para roberta). Por comentario, si un aspecto sale con signos opuestos en distintas oraciones queda `0`; si solo hay positivas o solo negativas, gana ese signo, y la evidencia es la oración más probable con ese signo.
7. **Test, una sola vez.** El modelo elegido y su umbral se fijaron por escrito antes de mirar el test; después se evaluó cada versión una vez.

### Criterios de anotación

Todo se anota por lo que dice el **texto**, nunca por la estrella del alumno. El formato es código de aspecto + signo, por ejemplo `CAL+ RIG0 CLI+`: `+` positivo, `-` negativo, `0` mixto o neutro; `ninguno` si no hay aspecto. `anotar_gold.py` trae esta guía dentro de su interfaz.

| Código | Se marca cuando el comentario habla de… | Positivo | Negativo |
|---|---|---|---|
| `RET` | Comentarios sobre trabajos y tiempos de respuesta del profesor | útil, detallado, rápido | inexistente, tardío, vago |
| `CLA` | Criterios de calificación, rúbricas, expectativas, qué evalúan los exámenes | claros, justos, coherentes con lo enseñado | opacos, arbitrarios, exámenes ajenos al contenido |
| `CAL` | Cómo enseña: explicaciones, clases, material | explica bien, interesante | confuso, aburrido |
| `ACC` | Disponibilidad y trato personal | disponible, empático, amable | inaccesible, grosero |
| `CAR` | Cantidad de tarea, lectura o trabajo | razonable o ligera | excesiva |
| `RIG` | Nivel de exigencia al calificar | exigente pero justo | injusto, imposible, castiga sin criterio |
| `ORG` | Organización del curso y proyectos | ordenado, plazos claros | caótico, improvisado |
| `CLI` | Ambiente de aula, humor, respeto | respetuoso, inspirador, divertido | hostil, sarcástico, condescendiente |
| `ASI` | Asistencia, quizzes sorpresa, puntos extra, participación | flexible, puntos extra | quizzes sorpresa, castigos estrictos |

**Criterio denso.** La primera anotación marcaba solo el aspecto principal (1.16 aspectos por comentario, frente a 2.5 al aplicar la guía al pie de la letra) y el acuerdo con un segundo anotador era bajo (kappa 0.49). Se fijó un criterio que anota **todo aspecto mencionado de forma explícita**, y se re-anotaron los 399 comentarios; el kappa humano–modelo subió a 0.72. Sus reglas, `D1` a `D15`:

- **D1** Cada aspecto mencionado se anota, aunque haya otros más importantes, una vez por comentario: «Great lectures, lots of homework» → `CAL+ CAR-`.
- **D2** Solo menciones explícitas: se anota lo que el texto dice, no lo que implica.
- **D3** `+` o `-` si el texto juzga el aspecto; `0` si lo menciona sin juicio o con juicios opuestos.
- **D4** Elogio o crítica general al profesor como enseñante («great teacher», «just reads from the book») → `CAL±`.
- **D5** Recomendar o rechazar sin dar razón («take him», «avoid at all cost») no marca nada.
- **D6** Persona amable o antipática → `ACC±`; ambiente, humor, entusiasmo o inspiración → `CLI±`.
- **D7** Dificultad sin más («hard», «easy A») → `RIG0`; el signo de Rigor sigue la regla de abajo.
- **D8** Carga: «lots», «too much» → `CAR-`; «not much», «light» → `CAR+`; una cantidad concreta sin adjetivo → `CAR0`.
- **D9** `ASI`: puntos extra o sin política de asistencia → `ASI+`; quizzes sorpresa o castigo por faltar → `ASI-`; asistencia obligatoria, quizzes regulares, participación o modalidad → `ASI0`.
- **D10** `RET` frente a `ACC`: devolver trabajos o notas con comentarios → `RET`; responder correos o dudas, estar disponible → `ACC`.
- **D11** `CLA` frente a `RIG`: qué se evalúa y su coherencia con lo enseñado → `CLA`; qué tan duro califica → `RIG`. «Fair grader» → `RIG+`; «exams are fair» → `CLA+`.
- **D12 a D15** El contexto (códigos de curso, nombre de la materia) no se anota. El sarcasmo se anota por su sentido real, y si hay duda razonable, `0`. Un comentario sin ninguno de los 9 aspectos, o que habla de otra cosa, es `ninguno`.

**Regla de Rigor.** Que «es difícil» no se convierta en «mal profesor» es la premisa del proyecto, y el gold la incumplía: el signo de RIG seguía a la estrella del alumno casi tanto como el de Calidad de clase (estrella media de `RIG+` 3.96, `RIG0` 3.24, `RIG-` 1.92). Se re-anotó solo el signo de RIG con esta regla: depende **únicamente** de lo que el texto dice sobre la exigencia o la forma de calificar. No cuentan el tono general del comentario, si recomienda la clase, si el profesor explica bien (eso es `CAL`) ni si los exámenes coinciden con lo enseñado (eso es `CLA`).

| Lo que dice el texto sobre la exigencia | Signo |
|---|---|
| La menciona sin calificarla: «hard», «tough grader», «strict», «easy A», «not hard» | `RIG0` |
| La califica como justa, valiosa o llevadera: «hard but fair», «tough but doable», «challenging but worth it» | `RIG+` |
| La califica como injusta, arbitraria o desmedida: «unfair», «impossible», «grades on a whim» | `RIG-` |
| Juicios opuestos sobre la exigencia en el mismo comentario | `RIG0` |
| La palabra no habla de exigencia («hard to hear», «easy to talk to») | no es Rigor: se quita |

*Prueba de aislamiento:* tapa todo lo que no hable de la exigencia; si el signo solo se sostiene por el resto del comentario, el signo de RIG es `0`. «Very hard class and he can't explain anything» → `CAL-` y `RIG0`; «Tough grader, but you learn so much because of it» → `RIG+`.

### Reglas del modelo

- Un comentario puede tener varios aspectos, y cada aspecto aparece una sola vez por comentario.
- La evidencia es un fragmento exacto del comentario original (hasta 280 caracteres), nunca una paráfrasis. `validar_review_aspecto.py` lo comprueba antes de cargar predicciones.
- Rigor nunca se fusiona con Calidad de clase: la dificultad no es positiva ni negativa por sí sola.
- La estrella del alumno no se usa para decidir aspecto ni polaridad: las etiquetas se justifican con el texto.
- No se usan como entrada el nombre del profesor, los códigos de materia ni columnas demográficas. Los nombres propios dentro del comentario se enmascaran como `[PROF]` antes del modelo.
- Un comentario sin aspecto reconocible no genera filas; no se fuerza una etiqueta.
- Los comentarios están en inglés y las citas se muestran en su idioma original.

### Decisiones de diseño

| Decisión | Razón |
|---|---|
| Medir contra un gold anotado a mano y separar dev de test | Sin una regla externa no hay F1 real; el test se usa una sola vez para que la cifra final sea honesta |
| Profesores reservados fuera del entrenamiento | Evita que el modelo memorice el estilo de un profesor e infle el F1 |
| Silver con un LLM en vez de anotar miles de comentarios a mano | El gold lo anotó una sola persona y anotar 4,000 a mano no era viable; el LLM se validó contra el gold antes de usarse |
| Entrenar un Transformer propio en vez de usar el LLM directamente | Corre gratis, en local y sin depender de un servicio externo |
| Regla de Rigor | Protege a los docentes exigentes: la dificultad no se convierte en mala evaluación |
| Meta de F1 revisada al techo de acuerdo entre anotadores | La meta de 0.85 se fijó antes de medir ese acuerdo y quedó por encima de lo que dos anotadores logran entre sí con esta guía |

Cómo se usa la salida en la interfaz, que depende de la confiabilidad medida: una tarjeta de fortaleza u oportunidad solo se muestra para un aspecto si el modelo acierta al menos el 60 % de las veces que marca ese signo, con al menos 10 casos (se mide el acierto del signo y no el F1, porque una tarjeta afirma «esto es una fortaleza» y importa que acierte cuando lo dice). Las citas excluyen groserías, insultos, lenguaje de odio y comentarios sobre apariencia, acento u origen; los conteos no cambian.

### Límites

- El gold lo anotó una sola persona. El segundo anotador (50 comentarios) fue Claude, así que el «techo» es un acuerdo **humano–modelo** (kappa 0.721; F1 de acuerdo 0.698, IC 95 % [0.62, 0.77]; detección 0.853), probablemente optimista frente a dos humanos. El acuerdo es más bajo justo en Rigor (kappa 0.592).
- Dev se usó también para validar el silver y para re-anotar Rigor, y el umbral se eligió ahí. Por eso la cifra que se reporta es la de test, que confirmó que no había sobreajuste (0.650 → 0.647).
- El test ya se usó una vez por versión (`data/uso_test.log`). Evaluar un modelo nuevo en test sería un segundo uso y debe declararse.
- Los datos son de Rate My Professors, en inglés; no son de la institución para la que se diseñó el sistema.
- El F1 global promedia nueve aspectos muy distintos: Retroalimentación, Asistencia, Carga y Organización tienen F1 bajo, así que no conviene leerlo como si valiera igual para todos.

### Códigos internos

En el código y en los documentos aparecen códigos como `M1.3` o `D7`. Los `D1` a `D15` son las reglas del criterio denso de arriba. Los `M` son requisitos numerados del módulo; los que se usan son `M1.1` (varios aspectos por comentario, cada uno una vez), `M1.3` (Rigor no se fusiona con Calidad de clase), `M1.5` (sin nombre ni demografía como entrada), `M2.2` (consolidación al comentario), `M2.5` (un solo umbral global calibrado en dev), `M3.1` (se publica la candidata con mayor F1 aspecto + polaridad en dev) y `M3.4` (prueba de identidad: cambiar el nombre del profesor no cambia las predicciones). El resto es numeración interna.

## Datos

**Fuente.** Los datos son una muestra de 20,000 reseñas del dataset «Big Data Set from RateMyProfessor.com for Professors' Teaching Evaluation», de Jibo He, publicado en Mendeley Data (versión 2, 4 de marzo de 2020) con licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/):

> He, J. (2020). *Big Data Set from RateMyProfessor.com for Professors' Teaching Evaluation* (Versión 2) [Conjunto de datos]. Mendeley Data. https://doi.org/10.17632/fvtfjyvw7d.2

`data/RateMyProfessor_Sample.csv` es el archivo `RateMyProfessor_Sample data.csv` de ese dataset, solo renombrado y sin otros cambios: mismo tamaño y mismo SHA-256 (`428e08dcc5de8c4b04cd10c6c0b057bc3550084b8de4faf0179f670e5c128aad`), 20,000 filas × 51 columnas. Según la ficha del dataset, las reseñas se obtuvieron por rastreo web de RateMyProfessor.com entre abril y julio de 2018.

**Cambios.** El resto de los CSV de `data/` se derivan de ese archivo:

- `separar_tablas.py` lo divide en tablas relacionales (`escuela`, `departamento`, `profesor`, `materia`, `review`). Elimina las columnas demográficas (`gender`, `race`, `asian`, `hispanic`, `nh_black`, `nh_white`), 19 duplicados exactos y 10 duplicados por clave de contenido (quedan 19,971 reseñas). Convierte `take_again` de «80%» a 0.8, rellena con «No reportado» los vacíos de `attence`, `for_credits`, `would_take_agains` y `grades`, y corrige artefactos de codificación en los textos.
- Se añadieron las anotaciones del proyecto (gold y silver) y las predicciones del modelo.

Los nombres de los profesores aparecen tal cual en los CSV; el modelo los enmascara antes de entrenar y predecir.

## Créditos

Claude (Anthropic) asistió en el desarrollo del código y en la evaluación del modelo: mediciones, análisis de errores e informes de resultados.

Claude también se usó como anotador automático en dos puntos del proceso: etiquetó el silver con `claude -p` (`generar_silver.py`) y fue el segundo anotador de 50 comentarios del gold, por lo que el acuerdo que se reporta es humano–modelo (ver [Límites](#límites)). El gold de 399 comentarios lo anotó a mano el autor del repositorio.

## Licencia

Cada parte del proyecto tiene su licencia:

| Qué | Licencia |
|---|---|
| Código: los scripts `.py`, el SQL, `environment.yml` y `requirements.txt` | [MIT](LICENSE) |
| Datos y anotaciones: `data/` (reseñas, gold, silver, predicciones), `sql/subida/*.csv`, `metricas/` y `silver/prompt_v1.md` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (ver [`data/LICENSE.md`](data/LICENSE.md)) |
| Documentación: este README, `MODEL_CARD.md` y `docs/` | CC BY 4.0 |
| Pesos del modelo (Hugging Face) | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) |

Las reseñas son de Jibo He (CC BY 4.0; ver [Datos](#datos)): al reutilizarlas hay que citarlo e indicar los cambios. Los tokenizadores de `data/modelos/*/tokenizer/` son copias de los de los modelos base (`roberta-base`, MIT; `distilroberta-base`, Apache-2.0) y conservan sus licencias.
