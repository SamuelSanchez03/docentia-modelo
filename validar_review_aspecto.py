#!/usr/bin/env python3
"""
validar_review_aspecto.py - Revisa que un review_aspecto*.csv cumpla el contrato antes de subirlo a Supabase.

  python validar_review_aspecto.py data/review_aspecto_v2b_roberta_base.csv

Comprueba: columnas del contrato, una sola version_modelo, ids consecutivos, aspectos y polaridades válidos,
review_id existentes y con texto real (no «No Comments»), evidencia no vacía, ≤ 280 caracteres y subcadena EXACTA del
comentario, y sin duplicados (review_id, aspecto, version_modelo). Imprime cobertura y la tabla aspecto × polaridad.
Sale con código 0 si todo está bien y 1 si algo falla.
"""
import sys

import pandas as pd

import absa_baseline as A

COLUMNAS = ["review_aspecto_id", "review_id", "aspecto", "polaridad", "evidencia", "version_modelo"]


def main(ruta):
    d = pd.read_csv(ruta)
    rev = pd.read_csv("data/review.csv", usecols=["review_id", "comentario"]).set_index("review_id").comentario
    reales = {int(i) for i, t in rev.items() if not A.es_relleno(t)}
    fallos = []

    def check(ok, msg):
        print(("ok    " if ok else "FALLA ") + msg)
        if not ok:
            fallos.append(msg)

    check(list(d.columns) == COLUMNAS, f"columnas = {COLUMNAS}")
    versiones = d.version_modelo.unique().tolist()
    check(len(versiones) == 1, f"una sola version_modelo ({versiones})")
    check(d.review_aspecto_id.tolist() == list(range(1, len(d) + 1)), "review_aspecto_id = 1..n")
    check(d.aspecto.isin(list(A.CODIGOS.values())).all(), "aspectos dentro de los 9 nombres canónicos")
    check(d.polaridad.isin(list(A.POL.values())).all(), "polaridad en {positivo, negativo, mixto_neutro}")
    check(d.review_id.isin(rev.index).all(), "todos los review_id existen en review.csv")
    check(d.review_id.isin(reales).all(), "ninguna fila sobre comentarios vacíos o «No Comments»")
    ev = d.evidencia.fillna("")
    check((ev.str.strip() != "").all(), "evidencia no vacía")
    check((ev.str.len() <= 280).all(), "evidencia ≤ 280 caracteres")
    malas = sum(1 for r, e in zip(d.review_id, ev) if r in rev.index and e not in rev[r])
    check(malas == 0, f"evidencia = subcadena exacta del comentario ({malas} que no lo son)")
    dup = int(d.duplicated(["review_id", "aspecto", "version_modelo"]).sum())
    check(dup == 0, f"sin duplicados (review_id, aspecto, version_modelo) ({dup})")

    print(f"\n{len(d):,} filas · {d.review_id.nunique():,} de {len(reales):,} comentarios con texto real tienen al menos un aspecto "
          f"({d.review_id.nunique() / len(reales):.1%}) · {len(d) / max(1, d.review_id.nunique()):.2f} aspectos por comentario con aspecto")
    print(d.pivot_table(index="aspecto", columns="polaridad", values="review_id", aggfunc="count", fill_value=0).to_string())
    print("\nRESULTADO:", "VÁLIDO" if not fallos else f"{len(fallos)} FALLA(S)")
    return 0 if not fallos else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
