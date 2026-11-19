# Doble anotación con el criterio denso: acuerdo **humano–modelo**

*29 de octubre de 2026 · `data/gold_doble_para_anotar.csv`, columna `anotacion_2` · 50 comentarios · sustituye a la medición del criterio escaso (`DOBLE_ANOTACION.md`)*

## 0. Actualización vigente (30-oct-2026): tras la regla de Rigor

Tú re-anotaste el signo de RIG del gold con la regla de Rigor; yo hice lo mismo con mis 50 (`anotacion_2`), sin ver tus nuevas etiquetas de RIG de estos comentarios. Cambié 4 de mis 29 menciones: 16173 `RIG+`→`RIG0`, 2178 `RIG-`→`RIG0`, y quité RIG en 5452 y 15962. Nada más cambió. Mi versión anterior está en `data/gold_v2_antes_rig/gold_doble_claude_antes_rig.csv`.

**Proyecto unipersonal:** no habrá segunda persona humana. Este es el acuerdo de referencia del proyecto, declarado como **humano–modelo** (desviación respecto de los requisitos originales).

| Medida (50 comentarios) | Antes de la regla de Rigor | **Vigente** |
|---|---:|---:|
| Kappa de Cohen (4 clases) | 0.745 [0.68, 0.81] | **0.721** [0.65, 0.78] |
| F1 de acuerdo aspecto + polaridad | 0.725 | **0.698** [0.62, 0.77] |
| F1 de acuerdo solo detección | 0.868 | **0.853** [0.80, 0.90] |
| Kappa sin los 6 comentarios que vi antes con tus etiquetas | — | 0.742 |
| Kappa solo en Rigor | — | 0.592 (acuerdo 0.76) |

**Dónde no coincidimos en Rigor (12 comentarios):**
- **Cuándo la exigencia es `+`:** en 4 casos yo pongo `+` y tú `0`: «expects a lot, but there are no surprises», «HIGH expectations, but that will make us successful», «grade her papers tough, but her comments… help», «tests can get rather hard, she gives bonus points to make up for it». la regla de Rigor tiene un ejemplo casi idéntico al primero como `+`; la frontera de «llevadera/valiosa» sigue siendo ambigua.
- **Qué cuenta como mención de exigencia:** yo dejo `RIG0` y tú no marcas RIG en «more intense», «disappointing level of difficulty», «hard quizes», «memorizing every little thing», «a little picky»; y al revés en «funny, honest and fair» (tú `RIG0`) y «final exam… ridiculous» (tú `RIG-`).
- «drop you a whole letter grade just because he can»: yo `RIG-`, tú sin RIG.

**Lectura:** el techo realista de aspecto + polaridad con esta guía es ≈ 0.70 (IC 0.62–0.77). Rigor es el aspecto menos estable entre anotadores; sus F1 deben leerse con cautela.

## 1. Procedencia: léelo antes de citar cualquier número

- **`anotacion_2` la escribió Claude (un modelo), no una persona.** Es acuerdo humano–modelo, **no** el kappa humano–humano que pedían los requisitos originales.
- **No fue a ciegas en sentido estricto.** (a) Anoté estos mismos 50 comentarios antes, con el criterio escaso, y vi tus etiquetas v1 de los 50. (b) **Escribí yo el criterio denso** después de ver las discrepancias, así que lo aplico mejor que alguien que no lo escribió. (c) De tus etiquetas v2 vi solo agregados (conteos y densidad), no comentario por comentario, hasta después de guardar las mías.
- **Consecuencia:** el acuerdo medido está probablemente **sesgado al alza** frente a un segundo anotador humano que lea la guía por primera vez. Tómalo como la mejor estimación optimista del techo, no como el techo.
- n = 50: los intervalos son anchos.

## 2. Resultado

| Medida | Criterio escaso (v1) | **Criterio denso** |
|---|---:|---:|
| Kappa de Cohen (4 clases) | 0.488 [0.42, 0.57] | **0.745** [0.68, 0.81] |
| Acuerdo observado por celda | 0.816 | 0.880 |
| F1 de acuerdo, aspecto + polaridad | 0.522 | **0.725** [0.65, 0.80] |
| F1 de acuerdo, solo detección | 0.576 | **0.868** [0.82, 0.91] |
| Signo coincide cuando ambos marcan | 90.6 % | 83.5 % (96 de 115) |
| Aspectos por comentario: tú / yo | 1.14 / 2.54 | 2.56 / 2.74 |
| De tus marcas, las que yo también marco (aspecto / aspecto y signo) | 93 % / 84 % | 90 % / 75 % |
| Comentarios `ninguno`: tú / yo | 11 / 3 | 3 / 3 |

## 3. Lectura

1. **El criterio denso funcionó:** la densidad se igualó y el kappa subió de 0.49 a 0.75. La guía del criterio denso es aplicable de forma bastante consistente.
2. **El techo realista del F1 de aspecto + polaridad es ≈ 0.73, no 0.85.** Dos anotadores que aplican la guía concuerdan en 0.73 (IC 0.65–0.80), y ese número es probablemente optimista. La meta original (≥ 0.85) queda por encima de lo que la guía permite medir con acuerdo. Los requisitos originales ya lo preveían: *«el criterio práctico es acercarse a ese techo»*. El techo de solo detección es ≈ 0.87.
3. **Las discrepancias de signo son casi todas `0` contra `+/−`, no inversiones.** De 19 diferencias de signo: 6 `+`→`0`, 6 `−`→`0`, 3 `0`→`−`, 3 `0`→`+` y **1** `−`↔`+`. La frontera «mención sin juicio» frente a «juicio leve» es lo difuso, no la dirección.
4. **Dónde la guía aún es ambigua** (cuenta de celdas distintas): CAL (7, p. ej. «reads out of the book», «smart teacher but time to retire»), CAR (9, la frontera `0`/`±` de D8: «only three tests», «100+ pages/week»), CLI (7, sobre todo quién marca humor/entusiasmo), CLA (8), ASI (6). Conviene aclarar esas reglas **para los 399**, no caso por caso.

## 4. Casos donde una etiqueta parece chocar con un ejemplo literal del criterio denso

Para que los revises tú; **no los cambio yo**. Si cambias algo, hazlo por regla y reporta el kappa tal como se midió antes de corregir.

- `8792` «VERY difficult to earn a good grade»: tú `RIG-`; D7 pone ese ejemplo como `RIG0`.
- `13639` «Just reads directly out of the book»: tú `CAL0`; D4 lo pone como `CAL-`.
- `10232` «hilarious… make early lit fun»: tú `CLI-`; el texto es claramente positivo (¿un desliz de tecla?).

## 5. Qué sigue pendiente

- **El kappa humano–humano sigue sin existir.** Una persona real que no haya visto el criterio denso comentado ni nuestras etiquetas debería anotar estos 50. Mis etiquetas pueden descartarse sin costo.
- **La meta debería reformularse:** declarar el techo de acuerdo medido (≈ 0.73 con aspecto + polaridad) y reportar el F1 del modelo **junto a él**, con el estado «en calibración» si no llega a 0.85.
