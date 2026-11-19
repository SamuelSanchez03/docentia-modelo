# Cómo ejecutar `absa_baseline.py` (v0.2) — orden y comandos

## Preparación (una vez)

```text
proyecto/
├── absa_baseline.py
└── data/
    ├── review.csv
    └── profesor.csv
```

```bash
pip install pandas numpy        # v0 solo necesita esto (Python 3.10+)
```

Todos los comandos se corren desde la carpeta `proyecto/`.

---

## Orden de ejecución

| # | Comando | Qué hace | Salida | ¿Quién? |
|---|---|---|---|---|
| 1 | `python absa_baseline.py particion` | Reserva 15% de profesores (semilla 42). Nada de ellos se usará para entrenar. | `data/particion_profesor.csv` | Script |
| 2 | `python absa_baseline.py muestra` | Muestra estratificada por estrellas, **solo de profesores reservados**, marcada `dev` (≈100) / `test` (≈300). Sin estrellas ni nombre en el archivo. | `gold_para_anotar.csv`, `gold_doble_para_anotar.csv` | Script |
| 3 | *Anotar a mano* la columna `anotacion` | Guía: criterio denso y regla de Rigor (ver «Criterios de anotación» en el README). Ej.: `CAL+ RIG0 CLI+`. Sin aspecto → escribe `ninguno`. Vacío = sin anotar. | `gold_para_anotar.csv` lleno | **Tú** |
| 3b | *Segunda persona* anota `gold_doble_para_anotar.csv` (columna `anotacion_2`), sin ver tus etiquetas | 50 comentarios | | Otra persona |
| 4 | `python absa_baseline.py etiquetar` | Etiqueta todos los comentarios con texto real (enmascara nombres). ~5 s en CPU. | `data/review_aspecto.csv` | Script |
| 5 | `python absa_baseline.py evaluar --gold gold_para_anotar.csv --conjunto dev --json metricas_dev.json` | F1 con IC bootstrap sobre **dev**. Aquí iteras y ajustas reglas. | pantalla + json | Script |
| 6 | `python absa_baseline.py identidad` | Prueba M3.4: cambiar el nombre del profesor no cambia las predicciones. | PASA / FALLA | Script |
| 7 | `python absa_baseline.py kappa --a gold_para_anotar.csv --b gold_doble_para_anotar.csv` | Acuerdo entre anotadores = cota realista del modelo. | pantalla | Script |
| 8 | `python absa_baseline.py evaluar --gold gold_para_anotar.csv --conjunto test --confirmar-test --json metricas_test.json` | **UNA sola vez**, con la versión ya congelada. | pantalla + json | Script |
| 9 | `python absa_baseline.py registrar --metricas metricas_test.json --descripcion "Reglas v0.2 + léxico"` | Escribe la fila de `modelo_version` (`validado` si F1 ≥ 0.85 en test; si no, `en_calibracion`). | `data/modelo_version.csv` | Script |

Los pasos 1, 2 y 4 ya están ejecutados sobre tus datos (los archivos van adjuntos), así que puedes empezar directamente por el paso 3.

## Protocolo: re-anotar solo el signo de Rigor (regla de Rigor, 30-oct-2026)

Regla: **regla de Rigor** (README, «Criterios de anotación»; el signo de RIG depende solo de lo que el texto dice de la exigencia; prueba de aislamiento).

1. **No abras** `data/gold_para_anotar.csv`, `data/gold_v2_antes_rig/` ni `docs/MEDICION_REGLAS_A2.md` hasta terminar: tienen los signos de RIG anteriores o ejemplos del gold.
2. Re-anota los 164 comentarios que tienen RIG (el archivo **no** trae el signo anterior):
   ```bash
   python anotar_gold.py --gold data/gold_rig_resign.csv --columna anotacion_rig --solo RIG
   ```
   Teclas: `+` `0` `-` ponen el signo directamente · `n` = «No es Rigor» (la palabra no habla de exigencia; se quitará RIG de ese comentario) · `→`/`←` navegar. Unos 30–45 min estimados.
3. Cuando estén los 164, fusiona (solo cambia RIG; deja respaldo en `data/gold_para_anotar.antes_rig.csv`; se niega si falta alguno):
   ```bash
   python absa_baseline.py fusionar-aspecto
   ```
4. Después: re-medir v0/v1 **solo en dev**. Las cifras de `MEDICION_V0_GOLD_V2.md`, `MEDICION_V1_GOLD_V2.md` y `MEDICION_REGLAS_A2.md` se calcularon con los signos de RIG anteriores.
5. Hecho (30-oct): las etiquetas de RIG de la doble anotación (`anotacion_2`, hechas por Claude) se re-decidieron con la regla de Rigor. Kappa humano–modelo vigente: 0.721 (ver `DOBLE_ANOTACION_V2.md`). Por ser un proyecto unipersonal, no habrá segunda persona humana (desviación respecto de los requisitos originales).

## Protocolo de re-anotación a ciegas del gold v2 (criterio denso)

El gold v1 (criterio escaso) está archivado en `data/gold_v1_escaso/`; los CSV de `data/` están vacíos y tienen la misma muestra. Reglas: **criterio denso** (README, «Criterios de anotación»).

1. **Antes de anotar, no abras** `data/gold_v1_escaso/`, `docs/MEDICION_V0_DEV.md` ni `docs/DOBLE_ANOTACION.md` (contienen etiquetas y errores del modelo). No corras `evaluar` hasta terminar los 399.
2. Anota los 399 con `python anotar_gold.py` (≈ 3–4 h estimadas con el criterio denso; hazlo en 2–3 sesiones, se retoma donde quedaste).
3. Si una regla te parece ambigua, apunta la duda aparte; se resuelve **por regla para los 399**, nunca comentario por comentario.
4. Al terminar: `python absa_baseline.py evaluar --conjunto dev --json metricas_dev_v2.json` (solo dev) y, cuando haya una segunda persona, `kappa`. El test se usa una sola vez al final.
5. La doble anotación (`anotacion_2`, 50 comentarios) debe hacerla **otra persona real** con la misma guía y sin ver tus etiquetas.

## Anotar el gold con la herramienta local (paso 3)

```bash
python anotar_gold.py                                                              # tú: columna 'anotacion'
python anotar_gold.py --gold data/gold_doble_para_anotar.csv --columna anotacion_2  # la segunda persona
```

Abre `http://127.0.0.1:8765`, muestra **solo el texto** (sin estrellas, nombre, dev/test ni predicciones) y guarda cada cambio al instante en el CSV. Atajos: `1`–`9` aspecto, `+` `-` `0` signo (repetir lo quita), `n` sin aspectos, `c` borrar, `→`/`←` navegar, `p` siguiente pendiente. Se puede cerrar y retomar: empieza en el primer pendiente. La primera vez crea `<archivo>.bak` con el original vacío. **Cierra el CSV en Excel mientras anotas.** La segunda persona debe usar su propia copia del proyecto o terminar antes de que tú empieces, para no ver tus etiquetas (el archivo de la doble no las contiene).

## Notas de la reconstrucción (23-oct-2026)

- `absa_baseline.py` v0.2 fue reconstruido; el archivo original se había perdido. `etiquetar` reproduce `data/review_aspecto.csv` byte a byte.
- Ejecútalo desde la carpeta del proyecto (donde están `absa_baseline.py` y `data/`). Con los parámetros por defecto los comandos 1 y 2 **solo verifican** (no sobrescriben).
- `identidad` ahora hace dos pruebas (A: cambio de nombre; B: título + apellido por palabra con carga). La B es la que demuestra que el enmascarado funciona.
- Los números de `evaluar`/`kappa`/`registrar` solo se han probado con un gold sintético. Ninguna cifra de calidad del modelo existe hasta que anotes el gold.

## Reglas que el script hace cumplir

- `evaluar --conjunto test` se **niega** sin `--confirmar-test` y deja un registro en `data/uso_test.log`; si repites la evaluación te avisa (M3.1).
- Solo cuenta comentarios **anotados**: la celda vacía se ignora. Por eso "sin aspecto" se escribe `ninguno`; si no, un comentario sin anotar parecería "sin aspecto" y falsearía las métricas.
- Avisa de tokens mal escritos (`CAL1`, `XYZ+`) y de un aspecto repetido con signos distintos (M1.1).
- Los comentarios vacíos y los **"No Comments"** (965 en tu archivo, relleno de la plataforma) no se etiquetan ni entran al gold.
- `registrar` nunca marca `validado` con métricas de `dev`.

## Para v1 (sentimiento preentrenado) y v2 (Transformer)

Requieren `pip install transformers torch` y acceso a Hugging Face (internet abierto o Colab):

```bash
python absa_baseline.py etiquetar --polaridad hf --salida data/review_aspecto_hf.csv
python absa_baseline.py evaluar --gold gold_para_anotar.csv --pred data/review_aspecto_hf.csv --conjunto dev --json metricas_dev_hf.json
```

v2 (fine-tuning con silver) es el siguiente hito y se hace en Colab; se prepara después de tener el gold y la línea base medida.
