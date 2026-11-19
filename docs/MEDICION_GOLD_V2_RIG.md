# Medición tras re-anotar el signo de Rigor

*30 de octubre de 2026 · dev: 99 comentarios, 212 aspectos · conjunto de prueba **sin usar** · métricas en `metricas_dev_v2rig_*.json`*

## 1. Verificación de la fusión

`fusionar-aspecto` se aplicó a los 164 comentarios que tenían RIG (los 164 re-anotados, ninguno pendiente). Comparado con el gold archivado (`data/gold_v2_antes_rig/`): **0** cambios en otros aspectos, **0** en comentarios sin RIG, **0** en texto o conjunto, **0** anotaciones vacías, y el RIG de cada comentario coincide con lo re-anotado. El respaldo automático (`data/gold_para_anotar.antes_rig.csv`) es idéntico al archivo archivado.

| Signo de RIG antes → después | n |
|---|---:|
| `0` → `0` | 64 |
| `−` → `0` | 24 |
| `−` → quitado («No es Rigor») | 19 |
| `+` → `0` | 18 |
| `0` → quitado | 12 |
| `+` → `+` | 11 |
| `+` → quitado | 9 |
| `−` → `−` | 6 |
| `0` → `−` | 1 |

Resultado: RIG en 124 comentarios (antes 164): `0` 106, `+` 11, `−` 7. El gold queda con 879 aspectos (2.20 por comentario). Cambiaron 83 comentarios: 18 de dev y 65 de test.

**40 menciones se quitaron** porque «hard/easy» no hablaba de exigencia. Eso cambia también la **detección** de RIG en el gold, no solo el signo; es correcto según la regla de Rigor, pero conviene saberlo al comparar cifras.

## 2. ¿El signo de Rigor sigue el tono?

Estrella media del comentario según el signo anotado (399 comentarios; estadística descriptiva del gold):

| | `+` | `0` | `−` |
|---|---:|---:|---:|
| RIG antes | 3.96 (n=38) | 3.24 (n=77) | 1.92 (n=49) |
| **RIG después** | 4.14 (n=11) | 3.19 (n=106) | 1.86 (n=7) |
| CAL (sin cambios) | 4.15 (n=145) | 3.00 (n=17) | 1.80 (n=126) |

El 85 % del Rigor queda neutro. Los pocos `+`/`−` que quedan siguen asociados a las estrellas, lo esperable cuando el texto dice «fair» o «unfair» de forma explícita. Ya no hay decenas de menciones de dificultad que heredan el tono del comentario.

## 3. Resultados (dev)

| Variante | F1 aspecto + polaridad | F1 detección | Exactitud de polaridad | Recall negativos | RIG: F1 / exactitud de signo |
|---|---:|---:|---:|---:|---:|
| v0 (`reglas-v0.2-lexico`) | 0.411 [0.346, 0.482] | 0.667 | 0.617 | 0.254 (16/63) | 0.67 / 0.85 |
| **v1 (`reglas-v0.2-hf`)** | **0.511** [0.444, 0.575] | 0.667 | 0.767 | 0.444 (28/63) | 0.67 / 0.85 |
| v0.3 léxico / v0.3 hf | 0.411 / 0.511 | 0.667 | igual que v0 / v1 | | |

Antes de re-anotar RIG: v0 0.360, v1 0.459 (RIG: F1 0.37, exactitud de signo 0.48). **Mejora pareada v1 − v0: +0.101, IC 95 % [+0.060, +0.147].** Las reglas del criterio denso (v0.3) siguen sin diferenciarse de v0.2.

## 4. Errores de v1 (dev)

| Tipo | n |
|---|---:|
| Aciertos | 102 |
| Aspecto omitido | **79** |
| Falso positivo | **54** |
| Signo equivocado | 31 (20 son `±` en el gold y `0` en v1; por aspecto: CAL 8, ASI 6, ACC 5, RIG 4) |

**El cuello de botella ya es la detección.** Con signo perfecto, v1 llegaría a 0.667 (su F1 de detección). Para acercarse al techo de acuerdo hay que detectar mejor: eso es v2.

## 5. Cautelas

- **Parte de la mejora en Rigor es por construcción:** tanto v0 como la regla de Rigor tratan la dificultad como neutra por defecto (M1.3). Es lo que la guía pide, pero el gold de dev ya **no es a ciegas en Rigor** (viste predicciones y errores de dev antes de re-anotar). El conjunto de prueba se re-anotó por regla, sin mirar predicciones de test, y sigue sin usarse.
- **El kappa humano–modelo (0.745) ya no es comparable en RIG:** mis etiquetas de la doble anotación siguen el D7 anterior. Sigue pendiente un segundo anotador humano.
- Con 99 comentarios y 30 menciones de RIG en dev, el F1 por aspecto es orientativo.
