#!/usr/bin/env python3
"""
separar_tablas.py  -  Divide RateMyProfessor_Sample.csv en tablas relacionales (un CSV por tabla).

Uso:
    python separar_tablas.py RateMyProfessor_Sample.csv data

Genera en la carpeta de salida (por defecto ./data):
    escuela.csv, departamento.csv, profesor.csv, materia.csv, review.csv,
    lote_importacion.csv, review_aspecto.csv (vacía, la llenará el modelo NLP),
    reporte_limpieza.json (conteos y avisos)

Reglas aplicadas:
  - Se eliminan las columnas demográficas (gender, race, asian, hispanic, nh_black, nh_white).
  - Se eliminan duplicados exactos y duplicados por clave de contenido.
  - take_again se conserva y se convierte "80%" -> 0.8 (vacío = vacío, nunca 0).
  - attence / for_credits / would_take_agains / grades: vacío -> "No reportado".
  - Materia: name_onlines si IsCourseOnline = 1, si no name_not_onlines; se descartan "NAN", "0", "0000", etc.
  - Se corrigen artefactos de encoding tipo \\xe2\\x80\\x93 y \\' en los textos.
"""
import sys
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd

ENTRADA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/RateMyProfessor_Sample.csv")
SALIDA = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data")
SALIDA.mkdir(parents=True, exist_ok=True)

FLAGS = [
    "tough_grader", "gives_good_feedback", "respected", "skip_class", "caring",
    "get_ready_to_read", "participation_matters", "clear_grading_criteria",
    "lecture_heavy", "lots_of_homework", "amazing_lectures", "inspirational",
    "hilarious", "accessible_outside_class", "extra_credit", "graded_by_few_things",
    "test_heavy", "group_projects", "so_many_papers", "beware_of_pop_quizzes",
]
DEMOGRAFICAS = ["gender", "race", "asian", "hispanic", "nh_black", "nh_white"]
NUMERICAS = [
    "year_since_first_review", "num_student", "star_rating", "diff_index",
    "student_star", "student_difficult", "help_useful", "help_not_useful",
    "word_comment", "IsCourseOnline",
] + FLAGS
REQUERIDAS = [
    "professor_name", "school_name", "department_name", "local_name", "state_name",
    "take_again", "post_date", "name_onlines", "name_not_onlines", "tag_professor",
    "attence", "for_credits", "would_take_agains", "grades", "comments",
] + NUMERICAS

reporte = {"archivo": ENTRADA.name, "avisos": []}


# ---------------------------------------------------------------- utilidades
def leer(ruta):
    """Lee todo como texto; solo '' cuenta como vacío (así 'NAN' queda como texto)."""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(ruta, dtype=str, keep_default_na=False,
                               na_values=[""], encoding=enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit("No pude leer el CSV ni como utf-8 ni como latin-1.")


_RE_ESC = re.compile(r"(?:\\x[0-9a-fA-F]{2})+")


def _decodificar(m):
    try:
        octetos = bytes(int(h, 16) for h in re.findall(r"\\x([0-9a-fA-F]{2})", m.group(0)))
        return octetos.decode("utf-8")
    except Exception:
        return m.group(0)


def limpiar_texto(valor):
    if pd.isna(valor):
        return valor
    v = _RE_ESC.sub(_decodificar, str(valor))
    v = v.replace("\\'", "'").replace('\\"', '"')
    return v.strip()


def moda(serie):
    m = serie.dropna().mode()
    return m.iloc[0] if len(m) else pd.NA


def codigo_valido(valor):
    if pd.isna(valor):
        return pd.NA
    v = str(valor).strip().upper()
    if v in {"", "NAN", "NONE", "NULL"} or re.fullmatch(r"0+", v):
        return pd.NA
    return v


def guardar(nombre, tabla):
    tabla.to_csv(SALIDA / f"{nombre}.csv", index=False, encoding="utf-8", na_rep="")
    reporte[f"filas_{nombre}"] = int(len(tabla))


def a_entero(serie):
    return pd.to_numeric(serie, errors="coerce").astype("Int64")


# ---------------------------------------------------------------- 1. lectura
raw = leer(ENTRADA)
if str(raw.columns[0]).startswith("Unnamed"):
    raw = raw.drop(columns=raw.columns[0])  # columna índice sobrante
faltan = [c for c in REQUERIDAS if c not in raw.columns]
if faltan:
    raise SystemExit(f"Faltan columnas en el CSV: {faltan}")
reporte["filas_entrada"] = int(len(raw))
reporte["columnas_entrada"] = int(raw.shape[1])
reporte["comentarios_no_vacios_entrada"] = int(raw["comments"].notna().sum())
raw.insert(0, "fila_origen", range(len(raw)))  # trazabilidad: fila 0-based del CSV original

# ---------------------------------------------------------------- 2. duplicados exactos
cols_dup = [c for c in raw.columns if c != "fila_origen"]
mask_exacto = raw.duplicated(subset=cols_dup, keep="first")
reporte["duplicados_exactos_eliminados"] = int(mask_exacto.sum())
df = raw[~mask_exacto].copy()

# ---------------------------------------------------------------- 3. columnas excluidas
df = df.drop(columns=[c for c in DEMOGRAFICAS if c in df.columns])

# ---------------------------------------------------------------- 4. limpieza de texto
for c in ["professor_name", "school_name", "department_name", "local_name",
          "state_name", "tag_professor", "name_onlines", "name_not_onlines",
          "attence", "for_credits", "would_take_agains", "grades", "comments"]:
    df[c] = df[c].map(limpiar_texto)
df.loc[df["comments"].fillna("") == "", "comments"] = pd.NA
df["department_name"] = df["department_name"].fillna("Sin departamento")

# ---------------------------------------------------------------- 5. tipos numéricos y fechas
for c in NUMERICAS:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["take_again"] = pd.to_numeric(
    df["take_again"].astype("string").str.replace("%", "", regex=False).str.strip(),
    errors="coerce") / 100.0

fecha = pd.to_datetime(df["post_date"], format="%m/%d/%Y", errors="coerce")
reporte["fechas_no_interpretables"] = int(df["post_date"].notna().sum() - fecha.notna().sum())
df["post_date"] = fecha.dt.strftime("%Y-%m-%d")
reporte["fecha_min"] = None if fecha.notna().sum() == 0 else str(fecha.min().date())
reporte["fecha_max"] = None if fecha.notna().sum() == 0 else str(fecha.max().date())

# ---------------------------------------------------------------- 6. materia
cod_online = df["name_onlines"].map(codigo_valido)
cod_presencial = df["name_not_onlines"].map(codigo_valido)
df["materia_codigo"] = cod_online.where(df["IsCourseOnline"] == 1, cod_presencial)

# ---------------------------------------------------------------- 7. categorías "No reportado"
df = df.rename(columns={
    "attence": "asistencia", "for_credits": "para_creditos",
    "would_take_agains": "volveria_a_tomar", "grades": "calificacion",
})
for c in ["asistencia", "para_creditos", "volveria_a_tomar", "calificacion"]:
    df[c] = df[c].fillna("No reportado")

# ---------------------------------------------------------------- 8. duplicados por clave de contenido
def huella(r):
    clave = "|".join([
        str(r["professor_name"]), str(r["school_name"]), str(r["post_date"]),
        str(r["comments"])[:60].lower(), str(r["student_star"]), str(r["materia_codigo"]),
    ])
    return hashlib.md5(clave.encode("utf-8")).hexdigest()


df["hash_contenido"] = df.apply(huella, axis=1)
mask_clave = df.duplicated(subset="hash_contenido", keep="first")
reporte["duplicados_por_clave_eliminados"] = int(mask_clave.sum())
df = df[~mask_clave].sort_values("fila_origen").reset_index(drop=True)

# ---------------------------------------------------------------- 9. tabla escuela
esc = (df.groupby("school_name", sort=True)
         .agg(local_name=("local_name", moda), state_name=("state_name", moda))
         .reset_index())
esc.insert(0, "escuela_id", range(1, len(esc) + 1))
esc = esc.rename(columns={"school_name": "nombre"})
esc_id = dict(zip(esc["nombre"], esc["escuela_id"]))

# ---------------------------------------------------------------- 10. tabla departamento
dep = (df[["school_name", "department_name"]].drop_duplicates()
         .sort_values(["school_name", "department_name"]).reset_index(drop=True))
dep["escuela_id"] = dep["school_name"].map(esc_id)
dep.insert(0, "departamento_id", range(1, len(dep) + 1))
dep_id = {(r.escuela_id, r.department_name): r.departamento_id for r in dep.itertuples()}
dep_out = dep[["departamento_id", "escuela_id", "department_name"]].rename(
    columns={"department_name": "nombre"})

# ---------------------------------------------------------------- 11. tabla profesor
atributos = ["year_since_first_review", "num_student", "star_rating", "diff_index",
             "take_again", "tag_professor"] + FLAGS
agg = {"department_name": moda}
agg.update({c: "first" for c in atributos})
grupo = df.groupby(["school_name", "professor_name"], sort=True)
prof = grupo.agg(agg).reset_index()

incons = {c: int((grupo[c].nunique(dropna=True) > 1).sum())
          for c in ["department_name"] + atributos}
incons = {k: v for k, v in incons.items() if v}
reporte["profesores_con_atributos_inconsistentes"] = incons
if incons:
    reporte["avisos"].append(
        "Hay profesores con valores distintos entre sus filas (ver profesores_con_atributos_inconsistentes). "
        "Se usó la moda (departamento) o el primer valor no vacío (resto).")

prof["escuela_id"] = prof["school_name"].map(esc_id)
prof["departamento_id"] = [dep_id[(e, d)] for e, d in zip(prof["escuela_id"], prof["department_name"])]
prof.insert(0, "profesor_id", range(1, len(prof) + 1))
prof_id = {(r.school_name, r.professor_name): r.profesor_id for r in prof.itertuples()}
prof["num_student"] = a_entero(prof["num_student"])
for c in FLAGS:
    prof[c] = a_entero(prof[c])
prof_out = prof[["profesor_id", "escuela_id", "departamento_id", "professor_name"] + atributos].rename(
    columns={"professor_name": "nombre"})

# ---------------------------------------------------------------- 12. tabla materia
mat = (df.loc[df["materia_codigo"].notna(), ["school_name", "materia_codigo"]]
         .drop_duplicates().sort_values(["school_name", "materia_codigo"]).reset_index(drop=True))
mat["escuela_id"] = mat["school_name"].map(esc_id)
mat.insert(0, "materia_id", range(1, len(mat) + 1))
mat_id = {(r.school_name, r.materia_codigo): r.materia_id for r in mat.itertuples()}
mat_out = mat[["materia_id", "escuela_id", "materia_codigo"]].rename(columns={"materia_codigo": "codigo"})

# ---------------------------------------------------------------- 13. tabla review
df["profesor_id"] = [prof_id[(s, p)] for s, p in zip(df["school_name"], df["professor_name"])]
df["materia_id"] = pd.array(
    [mat_id.get((s, c)) if pd.notna(c) else None for s, c in zip(df["school_name"], df["materia_codigo"])],
    dtype="Int64")
df["review_id"] = range(1, len(df) + 1)
df["lote_id"] = 1
for c in ["IsCourseOnline", "help_useful", "help_not_useful", "word_comment"]:
    df[c] = a_entero(df[c])
rev = df.rename(columns={"IsCourseOnline": "is_online", "comments": "comentario"})[[
    "review_id", "fila_origen", "lote_id", "profesor_id", "materia_id", "post_date", "is_online",
    "student_star", "student_difficult", "asistencia", "para_creditos", "volveria_a_tomar",
    "calificacion", "help_useful", "help_not_useful", "comentario", "word_comment", "hash_contenido",
]]

# ---------------------------------------------------------------- 14. integridad referencial
assert dep_out["escuela_id"].isin(esc["escuela_id"]).all(), "departamento -> escuela roto"
assert prof_out["departamento_id"].isin(dep_out["departamento_id"]).all(), "profesor -> departamento roto"
assert prof_out["escuela_id"].isin(esc["escuela_id"]).all(), "profesor -> escuela roto"
assert rev["profesor_id"].isin(prof_out["profesor_id"]).all(), "review -> profesor roto"
assert rev["materia_id"].dropna().isin(mat_out["materia_id"]).all(), "review -> materia roto"
assert rev["review_id"].is_unique and rev["hash_contenido"].is_unique

# ---------------------------------------------------------------- 15. escritura
guardar("escuela", esc)
guardar("departamento", dep_out)
guardar("profesor", prof_out)
guardar("materia", mat_out)
guardar("review", rev)
guardar("lote_importacion", pd.DataFrame([{
    "lote_id": 1,
    "archivo": ENTRADA.name,
    "fecha_importacion": datetime.now().isoformat(timespec="seconds"),
    "filas_leidas": reporte["filas_entrada"],
    "filas_insertadas": int(len(rev)),
    "filas_duplicadas": reporte["duplicados_exactos_eliminados"] + reporte["duplicados_por_clave_eliminados"],
    "filas_rechazadas": 0,
}]))
guardar("review_aspecto", pd.DataFrame(columns=[
    "review_aspecto_id", "review_id", "aspecto", "polaridad", "evidencia", "version_modelo"]))

# ---------------------------------------------------------------- 16. reporte y comparación con lo esperado
revs_por_prof = rev.groupby("profesor_id").size()
reporte["review_con_student_star_nulo"] = int(rev["student_star"].isna().sum())
reporte["review_sin_comentario"] = int(rev["comentario"].isna().sum())
reporte["review_sin_materia"] = int(rev["materia_id"].isna().sum())
reporte["profesores_con_1_review"] = int((revs_por_prof == 1).sum())

esperado_prd = {  # valores esperados de referencia (solo informativo, no detiene el script)
    "filas_entrada": 20000, "columnas_entrada": 51, "filas_escuela": 554,
    "filas_profesor": 1415, "profesores_con_1_review": 13,
    "comentarios_no_vacios_entrada": 19993, "review_con_student_star_nulo": 5,
}
reporte["comparacion_prd"] = {
    k: {"obtenido": reporte[k], "prd": v, "coincide": reporte[k] == v}
    for k, v in esperado_prd.items()
}

with open(SALIDA / "reporte_limpieza.json", "w", encoding="utf-8") as f:
    json.dump(reporte, f, ensure_ascii=False, indent=2)

print(f"\nListo. Archivos escritos en: {SALIDA.resolve()}\n")
for k in ["filas_entrada", "duplicados_exactos_eliminados", "duplicados_por_clave_eliminados",
          "filas_escuela", "filas_departamento", "filas_profesor", "filas_materia", "filas_review"]:
    print(f"  {k:36s} {reporte[k]:>8,}")
print("\nComparación con lo esperado (informativa):")
for k, v in reporte["comparacion_prd"].items():
    marca = "OK " if v["coincide"] else "DIF"
    print(f"  [{marca}] {k:32s} obtenido={v['obtenido']:<8} prd={v['prd']}")
if reporte["avisos"]:
    print("\nAvisos:")
    for a in reporte["avisos"]:
        print("  -", a)
