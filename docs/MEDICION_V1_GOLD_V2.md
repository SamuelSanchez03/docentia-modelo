# Medición de v1 (`reglas-v0.2-hf`) contra el gold v2 (criterio denso)

> **Superado (30-oct-2026):** cifras con los signos de Rigor anteriores. Las vigentes están en `MEDICION_GOLD_V2_RIG.md` (v0 0.411, v1 0.511 en dev).

*29 de octubre de 2026 · 99 comentarios dev, 218 aspectos · conjunto de prueba **sin usar** · métricas en `metricas_dev_v2_hf.json` · salida en `data/review_aspecto_hf.csv` (**no** cargada a Supabase)*

## 1. Qué es v1 y cómo se corrió

Mismas reglas de detección que v0; cambia **solo la polaridad** de los aspectos que no son «solo reglas» (CAL, ACC, CLA, RET, ORG, CLI): en vez del léxico, el signo de la cláusula lo da `cardiffnlp/twitter-roberta-base-sentiment-latest`. CAR, RIG y ASI siguen con frases-señal (diseño: «hard» o «lots of homework» no son «mal profesor»).

- Entorno: conda `ecid` (Python 3.11, torch 2.12.0+cu130 sin GPU, transformers 5.11.0, numpy 2.4.2, pandas 3.0.1). Modelo descargado de Hugging Face a `~/.cache/huggingface` (~0.5 GB; el aviso `UNEXPECTED pooler.*` es normal al cargarlo para clasificación).
- Tiempo: **≈ 8 min en CPU** para 18,996 comentarios y 22,696 cláusulas únicas (el objetivo N2 era < 30 min).
- Integridad: mismas 32,944 parejas (review, aspecto) que v0; 0 evidencias que no sean subcadena exacta; 0 duplicados. La polaridad cambió en 5,723 filas: 2,510 neutras → positivas, 1,999 neutras → negativas, 638 y 330 de positivo a otro signo.

## 2. Resultado (dev)

| Métrica | v0 | **v1** |
|---|---:|---:|
| F1 micro aspecto + polaridad (meta 0.85) | 0.360 [0.293, 0.428] | **0.459** [0.397, 0.521] |
| F1 micro solo detección | 0.667 | 0.667 (sin cambio, por diseño) |
| F1 macro (aspecto + polaridad) | 0.268 | 0.376 |
| Exactitud de polaridad (aspectos bien detectados) | 0.541 | **0.689** |
| Recall de polaridad negativa | 0.239 (17/71) | **0.408** (29/71) |
| Precisión de polaridad negativa | 0.607 | 0.644 |

**Mejora pareada del F1 aspecto + polaridad: +0.100, IC 95 % [+0.059, +0.145]** (bootstrap sobre los mismos comentarios; v1 gana en el 100 % de 2,000 remuestras). Los intervalos de arriba se solapan porque no están pareados; la diferencia sí es robusta.

## 3. Lo que queda en el signo (dev)

De los 135 aspectos bien detectados, v1 falla el signo en 42 (v0: 62). En 32 de ellos el gold tiene `+`/`-` y v1 predice `0`.

| Grupo | Errores de signo | Por aspecto (aciertos / detectados) |
|---|---:|---|
| CAR, RIG, ASI (solo reglas, no usan el modelo) | **24** | RIG 14/29, ASI 4/10, CAR 4/7 |
| CAL, ACC, CLA, RET, ORG, CLI (usan el modelo) | 18 | CAL 34/42, ACC 24/29, CLI 9/12 |

## 4. Techos y lectura

- **Techo de v1:** con signo perfecto sobre lo que v0 ya detecta, el F1 aspecto + polaridad sería **0.667** (la detección). v1 está en 0.459. Si solo se arreglara el signo de CAR/RIG/ASI, el F1 llegaría hasta ≈ 0.58.
- **Referencia de acuerdo:** el F1 de acuerdo humano–modelo con el criterio denso fue 0.725 en aspecto + polaridad y 0.868 en detección (ver `DOBLE_ANOTACION_V2.md`; probablemente optimista). La detección de v0/v1 (0.667) está 0.20 por debajo.
- **Para pasar de 0.667 hay que mejorar la detección** (v0 omite 83 de 218 aspectos): eso es trabajo de v2.
- **Dev tiene 99 comentarios.** Los F1 por aspecto con `n_gold` < 10 (Retroalimentación, Organización, Clima en parte) no deben interpretarse.
- v1 sigue siendo una **candidata**: no está registrada en `modelo_version`, no se subió a Supabase y no se midió en test.
