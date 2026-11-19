# Doble anotación del gold: acuerdo **humano–modelo** (no humano–humano)

> **Superado por `DOBLE_ANOTACION_V2.md` (29-oct-2026):** con el criterio denso el kappa humano–modelo subió de 0.49 a 0.75.

> **Estado (25-oct-2026):** se adoptó el criterio **denso (A)**. Los dos archivos de anotación descritos aquí (tuyo y de Claude) están archivados en `data/gold_v1_escaso/`; `data/gold_para_anotar.csv` y `data/gold_doble_para_anotar.csv` se regeneraron **vacíos** con la misma muestra. La regla nueva es el criterio denso (descrito en el README). La doble anotación debe repetirla **una persona real**.

*25 de octubre de 2026 · `data/gold_doble_para_anotar.csv`, columna `anotacion_2` · copia del original vacío en `gold_doble_para_anotar.csv.bak`*

## 1. Procedencia (leer antes de citar cualquier número)

- **Quién anotó:** `anotacion_2` la escribió **Claude (un modelo de lenguaje)**, no una persona. El acuerdo medido es entre tú y un modelo. **No es el kappa humano–humano que pedían los requisitos originales**; sirve como señal, no como sustituto, y debe reportarse así en el documento final.
- **Cómo:** leyendo solo el texto de los 50 comentarios, con la guía de anotación. Sin ver tus etiquetas ni las predicciones de v0 de esos comentarios.
- **Contaminación declarada:** 6 de los 50 (`1460, 5137, 13966, 16173, 19023, 19604`) ya los había visto **con tus etiquetas** en la tabla de errores de `MEDICION_V0_DEV.md`. Los anoté igual, pero el acuerdo se reporta con y sin ellos (cambia casi nada: kappa 0.488 → 0.492).
- **Sesgo propio de un modelo:** tiende a marcar más aspectos que una persona. Un segundo anotador humano podría quedar más cerca de ti o más lejos; no se puede inferir de aquí.

## 2. Resultado (50 comentarios, 450 celdas comentario × aspecto)

| Medida | Valor |
|---|---:|
| Kappa de Cohen (4 clases: sin aspecto, +, −, 0) | **0.488** (IC 95 % bootstrap 0.42–0.57) |
| Acuerdo observado por celda | 0.816 |
| Kappa sin los 6 contaminados (n = 44) | 0.492 |
| F1 de acuerdo (tú como referencia): aspecto + polaridad / solo detección | 0.522 / 0.576 |
| Cuando ambos marcan el aspecto, coinciden en el signo | 90.6 % (53 casos) |
| De tus 57 marcas: mismo aspecto / mismo aspecto y signo | 93 % (53) / 84 % (48) |
| De mis 127 marcas, las que tú también marcas | 42 % (53) |
| Aspectos por comentario (en estos 50) | tú 1.14 · yo 2.54 |
| Comentarios `ninguno` | tú 11 · yo 3 |

Con 50 comentarios el intervalo es ancho; es orden de magnitud, no una medida fina.

## 3. Qué dice

**Casi toda la discrepancia es densidad, no significado.** De 83 celdas distintas, 74 son «solo yo» (aspectos que marqué y tú no), 4 son «solo tú» y 5 son de signo. Mis marcas contienen casi todas las tuyas; las que tú no tienes son sobre todo:

- **Elogio o crítica general al docente como enseñante** («good teacher», «worst professor… it really is him», «very knowledgeable»): yo lo marco `CAL±`, tú lo dejas en `ninguno` o sin CAL (CAL: 23 celdas; 6 comentarios de una línea).
- **Menciones sin juicio (`0`)** de carga, asistencia o formato («100+ pages…», «quiz every class», «class participation», «this class was online»): yo 38 celdas con `0`, tú 18.
- **Aspectos secundarios** en comentarios largos: tú te quedas con el más saliente (a veces 1) y yo marco todos los que se mencionan.

Menos frecuente, pero real: tu `RIG-` para «VERY difficult to earn a good grade» (8792) choca con la propia regla de la guía de anotación («difficult» sin más es `RIG0`).

## 4. Consecuencias para lo ya medido

1. **El 0.30 de v0 en dev se midió contra un gold escaso** (1.16 aspectos/comentario en tus 399; el dev tiene 113 aspectos en 99 comentarios; v0 predice 187 = 1.89 por comentario). Una parte de sus «falsos positivos» (108 de 176 errores) son menciones que la guía manda anotar y que tu gold no tiene. No se sabe cuántas sin una anotación consistente. **No des el 0.30 como cifra de la calidad de v0**; es una cota inferior contra un criterio estricto.
2. **El techo realista con el criterio actual es bajo:** el F1 de acuerdo entre dos anotadores sobre esta guía es 0.52–0.58, y el F1 de detección de v0 (0.53) ya está en ese orden. Mientras la guía no fije cuánto cuenta como «mención», 0.85 no es alcanzable ni medible.
3. **El silver para entrenar v2 heredará la misma ambigüedad:** el prompt sigue la guía de anotación. Si el criterio no se fija antes, el modelo aprenderá una mezcla.

## 5. Qué decidir (decisión tuya; yo recomiendo A)

La pregunta es **qué cuenta como mención anotable**. Dos criterios coherentes con el producto:

| | A. Denso (recomendado) | B. Escaso |
|---|---|---|
| Regla | Se anota todo aspecto con mención explícita en el texto; elogio/crítica general al enseñante = `CAL±`; mención sin juicio = `0` | Solo el o los aspectos más salientes del comentario |
| Por qué | Es lo que el reporte necesita (conteos por aspecto, umbral de menciones I1.2) y lo que el modelo puede aprender de forma consistente | Es lo que ya hiciste; pero «saliente» es subjetivo y fija un techo bajo |
| Costo | Re-anotar los 399 (≈ 2–3 h) y los 50 | Ninguno, pero v0/v2 se medirán contra algo que no pueden predecir bien |

Si eliges A, el procedimiento válido es: escribir la regla en la guía de anotación, **re-anotar los 399 comentarios sin mirar predicciones ni mis etiquetas**, y repetir la doble anotación con otra persona real. Cambiar etiquetas una por una porque el modelo no coincide invalida la medición (fuga de información).

Mis `anotacion_2` pueden servir como borrador de referencia **solo** si decides revisarlas tú, con el riesgo de anclaje (tenderás a aceptarlas). Para el conjunto de prueba (300) lo más defendible es que la anotación sea tuya y a ciegas.
