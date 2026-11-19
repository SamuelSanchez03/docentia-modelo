# Licencia de `data/`

Todo lo que hay en esta carpeta se distribuye bajo **Creative Commons Atribución 4.0 Internacional (CC BY 4.0)**: <https://creativecommons.org/licenses/by/4.0/>. Eso incluye las reseñas, las tablas derivadas, el gold, el silver y las predicciones.

**Excepción:** los tokenizadores de `modelos/*/tokenizer/` son copias de los de los modelos base y conservan su licencia (`roberta-base`: MIT; `distilroberta-base`: Apache-2.0).

## Atribución

Las reseñas provienen de este dataset, también publicado con CC BY 4.0:

> He, J. (2020). *Big Data Set from RateMyProfessor.com for Professors' Teaching Evaluation* (Versión 2) [Conjunto de datos]. Mendeley Data. https://doi.org/10.17632/fvtfjyvw7d.2

Al reutilizar estos datos hay que citar esa fuente, enlazar la licencia e indicar los cambios.

## Cambios respecto del original

- `RateMyProfessor_Sample.csv` es el archivo `RateMyProfessor_Sample data.csv` del dataset, solo renombrado y sin otros cambios (SHA-256 `428e08dcc5de8c4b04cd10c6c0b057bc3550084b8de4faf0179f670e5c128aad`).
- Las tablas `escuela.csv`, `departamento.csv`, `profesor.csv`, `materia.csv` y `review.csv` se generan con `separar_tablas.py`: sin columnas demográficas, sin 29 duplicados, con algunos campos normalizados y la codificación de los textos corregida.
- Las anotaciones (gold, silver) y las predicciones del modelo las añadió este proyecto.

El detalle está en la sección «Datos» del README del repositorio.
