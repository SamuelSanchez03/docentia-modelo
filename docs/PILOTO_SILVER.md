# Piloto del silver con `claude -p` (plan Pro)

*30 de octubre de 2026 · modelo `sonnet` · prompt `silver/prompt_v1.md` (hash `373bda23`) · script `generar_silver.py` · conjunto de prueba **sin usar***

## 1. Qué se corrió

| Etapa | Comentarios | Llamadas |
|---|---:|---:|
| Prueba mínima | 3 (entrenamiento) | 1 |
| Control de calidad | 99 (todo dev del gold) | 6 (1 reintento) |
| Piloto | 97 más hasta completar 100 de entrenamiento | 7 (1 lote descartado por formato y repetido tras corregir el script) |
| **Total** | **≈ 260 comentarios-llamada** | **14** |

`claude -p` corre con tu sesión Pro, sin herramientas, con el prompt propio como sistema y desde una carpeta vacía (no lee el proyecto). `ANTHROPIC_API_KEY` no está definida, así que no hubo cobro de API.

## 2. Consumo medido

| Por comentario | Valor |
|---|---:|
| Tiempo | ≈ 0.7 s (lotes de 20 en 12–16 s) |
| Tokens de salida | ≈ 96 |
| Tokens de entrada | ≈ 250 (casi todo el prompt fijo leído de caché; ≈ 2,200 por llamada) |
| Costo **equivalente** si fuera API | ≈ 0.0015 USD (registrado por la CLI; con tu plan no se cobra) |

**Proyección para 4,000 comentarios** (≈ 200 llamadas, con ~10 % de reintentos): ≈ 50 min de llamadas, ≈ 0.4 M tokens de salida, ≈ 1 M de entrada (mayormente caché), ≈ 6–7 USD equivalentes. El piloto equivale a ≈ 6–7 % de una corrida completa: el porcentaje que haya subido tu medidor de uso en claude.ai (Configuración → Uso) multiplicado por ≈ 15 da una estimación de lo que costaría en límites del plan.

## 3. Control de calidad contra tu gold de dev (desviación respecto de los requisitos originales)

| Métrica | Etiquetador LLM (prompt v1) | Umbral | v1 (reglas + sentimiento) | Acuerdo humano–modelo |
|---|---:|---:|---:|---:|
| F1 aspecto + polaridad | **0.693** [0.648, 0.740] | ≥ 0.60 | 0.511 | 0.698 |
| F1 detección | **0.779** [0.744, 0.813] | ≥ 0.75 | 0.667 | 0.853 |
| Exactitud de polaridad | 0.889 | | 0.767 | |
| Recall de negativos | 0.841 (53/63) | | 0.444 | |
| Aspectos predichos / gold | 276 / 212 | | 187 / 212 | |

**Pasa el control de calidad.** Es la evaluación n.º 1 en dev del prompt (máximo 2). Integridad: 0 evidencias que no sean subcadena exacta, 0 duplicados.

Puntos débiles: **sobre-detección** (276 predichos contra 212 del gold), sobre todo en ORG (15 contra 6), ASI (28 contra 14) y CLA (19 contra 11). Carga de trabajo tiene el recall más bajo (0.40).

## 4. Rigor en el silver (indicativo, 100 comentarios)

RIG: 27 `0`, 5 `+`, 6 `−` (71 % neutro; en el gold, 85 %). El silver tiene 2.92 aspectos por comentario (gold: 2.20), coherente con la sobre-detección. Los pocos `RIG−` están en comentarios de 1 estrella; con n = 6 no se puede concluir más.

## 5. Problemas encontrados y corregidos

- El modelo a veces repite un aspecto con dos signos en la misma oración (`RIG0` y `RIG+`). Antes se descartaba el lote completo; ahora se combinan con la regla M2.2/D3 (opuestos → `0`; neutro + signo → signo). No cambia el prompt.

## 6. Decisión siguiente

- **Seguir con prompt v1** para los 3,900 restantes; la sobre-detección se compensa con el umbral de detección de v2b (§3.3 del plan), calibrado primero en la validación interna del silver.
- O **una única versión v2 del prompt** (la última permitida) que endurezca ORG, ASI y CLA, y volver a medir en dev antes de seguir.

## 7. Corrida completa (30-oct-2026, 19:46–20:37)

- **4,000 de 4,000** comentarios etiquetados con prompt v1 y `sonnet`, en 205 llamadas (~50 min), sin topar con el límite del plan. Hubo 1 lote descartado y luego repetido: el separador de oraciones dejaba una «oración» `)` que el modelo omitía. La validación ahora acepta omitir oraciones sin letras ni dígitos (se toman sin aspectos).
- Consumo total registrado: ≈ 0.97 M tokens de entrada (casi todo caché) y 0.40 M de salida; costo **equivalente** de API ≈ 6.1 USD (no cobrado).
- `data/silver/silver_oraciones.csv`: **3,998 comentarios** (2 son solo puntos: `....`, `...`), **15,259 oraciones**, 16 % sin aspecto, 2.93 aspectos por comentario (gold: 2.20).
- Integridad: 0 comentarios del gold, 0 de profesores reservados, 0 oraciones con el nombre del profesor sin enmascarar; una sola versión de prompt y modelo.
- Oraciones por aspecto (`+`/`−`/`0`): CAL 3892/2152/377 · ACC 1792/829/75 · RIG 289/208/1839 · CLI 969/192/46 · CLA 374/417/198 · ASI 264/101/798 · CAR 129/371/442 · ORG 219/409/233 · RET 136/171/19. Los aspectos raros quedan con cientos de ejemplos gracias al sobremuestreo.
- **Rigor:** 75 % neutro a nivel comentario (gold: 85 %). `RIG+` 273 (4.16 estrellas de media), `RIG−` 162 (1.93). El silver firma Rigor algo más que el gold: vigilar en dev si v2 pone signo a Rigor de más.
