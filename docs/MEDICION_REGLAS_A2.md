# Reglas de signo del criterio denso (D7–D9) para Rigor, Carga y Asistencia: resultado

> **Decisión (30-oct-2026): opción A, ya aplicada.** D7 se aclaró con la regla de Rigor y se re-anotó el signo de RIG. Cifras vigentes en `MEDICION_GOLD_V2_RIG.md`.

*30 de octubre de 2026 · dev: 99 comentarios, 218 aspectos · conjunto de prueba **sin usar** · código: `absa_baseline.py etiquetar --reglas v0.3` (el valor por defecto sigue siendo `v0.2`, que reproduce `review_aspecto.csv` byte a byte)*

## 1. Qué se hizo

Se escribieron frases-señal de signo para RIG, CAR y ASI siguiendo literalmente D7, D8 y D9 del criterio denso (`REGLAS_A2` en `absa_baseline.py`). **No se miraron los errores de dev antes de escribirlas.** La detección (patrones) no cambia. Las 19 pruebas literales (los ejemplos de la propia regla: «hard but fair» → `+`, «VERY difficult» → `0`, «lots of homework» → `-`, «extra credit» → `+`, «beware of pop quizzes» → `-`, «attendance is mandatory» → `0`, etc.) pasan. Versiones nuevas: `reglas-v0.3-lexico` y `reglas-v0.3-hf` (archivos `data/review_aspecto_v03*.csv`, no subidos a Supabase).

## 2. Resultado: ninguno

| (dev) | F1 aspecto + polaridad | Exactitud de polaridad |
|---|---:|---:|
| v0.2 léxico | 0.360 | 0.541 |
| v0.3 léxico | **0.360** | 0.541 |
| v1 (v0.2 + modelo de sentimiento) | 0.459 | 0.689 |
| v0.3 + modelo de sentimiento | **0.459** | 0.689 |

Las reglas del criterio denso cambian solo **122 de ~10,600 filas** de RIG/CAR/ASI (CAR 53, RIG 42, ASI 27; 0 filas de otros aspectos) y **ninguno de esos cambios altera un aspecto del gold de dev**. Las reglas v0.2 ya eran casi equivalentes a D7–D9. **Los 24 errores de signo de RIG/CAR/ASI no se deben a que las frases-señal no sigan la regla escrita.**

## 3. Por qué fallan (diagnóstico de los 24 errores de dev; solo para entender)

| Causa | n aprox. | ¿Se arregla con reglas? |
|---|---:|---|
| El signo de **Rigor** parece juzgado sobre el comentario completo, no sobre la oración: «Tough marker.» (+) en un comentario que sigue con «it was a privilege»; «She expects a lot, but there are no surprises.» (+); «very hard teacher doesn't explain well…» (−) | ≈ 10 | No con frases-señal; exige juzgar el tono del comentario |
| Etiquetas del gold que se apartan de la letra del criterio denso (D7: «hard»/«easy» sin más = `0`; D9: «participation grade», «does take attendance» = `0`): «Not hard.» (+), «DONT TAKE… IF YOU WANT AN EASY A» (+), «She does take attendance.» (−) | ≈ 6 | No: es criterio de anotación |
| Huecos reales de reglas: «didn't **even** take attendance», «killed us with the amount of homework», «more homework than she can grade» | ≈ 4 | Sí, parcialmente |
| Falso positivo de patrón: «He is **hard** to hear» (RIG); `fairly` en «fairly easy A» cuenta como «fair» (heredado de v0.2) | ≈ 2 | Sí (arreglos mínimos; **informados por dev**) |

Estos arreglos de reglas están **informados por dev** y por eso no los apliqué: cualquier regla escrita mirando esos 99 comentarios ya no se puede validar en ellos, solo en test.

## 4. Hallazgo sobre Rigor y el premisa del proyecto

El signo anotado en Rigor sigue a la estrella del alumno casi tanto como el de Calidad de clase (estrella media del comentario según el signo anotado, 399 comentarios; estadística descriptiva del gold, no del modelo):

| Aspecto | `+` | `0` | `-` | `+` menos `-` |
|---|---:|---:|---:|---:|
| Calidad de clase | 4.15 | 3.00 | 1.80 | +2.35 |
| **Rigor** | **3.96** | **3.24** | **1.92** | **+2.04** |
| Carga | 4.21 | 3.40 | 2.70 | +1.51 |
| Asistencia | 3.62 | 3.53 | 2.83 | +0.79 |

Los alumnos que dicen «unfair» o «hard and unfair» sí dan pocas estrellas, así que parte de esta relación es esperable. Pero un `RIG-` con 1.92 estrellas de media, comparado con un `RIG0` de 3.24, es compatible con anotar **el tono** del comentario cuando se menciona dificultad. Eso choca con M1.3 y con la razón de ser del proyecto: separar el rigor de la calidad para no penalizar a los docentes exigentes («castigo por la exigencia»). **Un modelo entrenado o medido contra ese gold aprendería justamente ese sesgo.**

No es una conclusión demostrada: es una hipótesis con indicios que conviene decidir de forma explícita.

## 5. Opciones

- **A. Aclarar D7 y re-anotar solo los signos de RIG** (≈ 164 menciones; unas 87 con signo). Regla: `RIG±` solo si el texto califica la *exigencia* («hard but fair/worth it», «unfair/impossible/arbitrary»); no se infiere del tono del comentario. Es por regla y uniforme, pero ya viste las predicciones de dev, así que esa parte del gold deja de ser «a ciegas» y el F1 de dev pierde parte de su valor; el test sí sigue limpio.
- **B. Dejar el gold como está** y pasar a v2, aceptando que el signo de Rigor reflejará el tono del comentario, y declarando esa limitación en el reporte.
- En cualquier caso: v1 sigue siendo la mejor candidata actual (0.459 en dev), con techo 0.667 por la detección.
