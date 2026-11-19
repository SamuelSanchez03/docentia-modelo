#!/usr/bin/env python3
"""
entrenar_v2a.py - v2a: embeddings de oración (all-MiniLM-L6-v2) + regresión logística por aspecto (9 cabezas × 4 clases).

  python entrenar_v2a.py entrenar                 # elige C y umbral en la validación interna del silver; reentrena con todo
  python entrenar_v2a.py predecir --conjunto dev  # -> data/modelos/v2a/review_aspecto_v2a_dev.csv (para `absa_baseline.py evaluar`)
  python entrenar_v2a.py predecir --conjunto todos  # -> data/review_aspecto_v2a.csv (solo si v2a resulta elegida)

Mismo preprocesamiento que v0 y el silver: absa_baseline.frases() + crear_mascara(); la evidencia es la oración ORIGINAL.
Decisión por oración: el aspecto está presente si 1 - p(no_menciona) > t; signo = argmax entre +, -, 0.
Consolidación al comentario con la regla M2.2. El dev NO se usa para elegir C ni t.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

import absa_baseline as A

DIR = Path("data/modelos/v2a")
EMB = "sentence-transformers/all-MiniLM-L6-v2"
VERSION = "v2a-minilm-lr"
COD = list(A.CODIGOS)
SIG = {1: "+", 2: "-", 3: "0"}
SEMILLA = 42


def _codificar(textos):
    m = SentenceTransformer(EMB, device="cpu")
    return m.encode(list(textos), batch_size=64, normalize_embeddings=True, show_progress_bar=False)


def _probs(modelos, X):
    """dict aspecto -> matriz (n, 4) con columnas en el orden de clases 0..3 (0 = no_menciona)."""
    out = {}
    for c in COD:
        clf = modelos[c]
        p = np.zeros((len(X), 4))
        p[:, clf.classes_] = clf.predict_proba(X)
        out[c] = p
    return out


def _consolidar(ids, P, t):
    """Por comentario: {cod: (signo, fila_evidencia)} con presencia 1-p0>t, signo argmax(+,-,0) y regla M2.2."""
    res = {}
    for fila, rid in enumerate(ids):
        for c in COD:
            p = P[c][fila]
            if 1 - p[0] > t:
                k = 1 + int(np.argmax(p[1:]))
                res.setdefault(rid, {}).setdefault(c, []).append((SIG[k], p[k], fila))
    final = {}
    for rid, asp in res.items():
        for c, lst in asp.items():
            pos = any(s == "+" for s, _, _ in lst)
            neg = any(s == "-" for s, _, _ in lst)
            sig = "0" if pos == neg else ("+" if pos else "-")
            cand = [x for x in lst if x[0] == sig] or lst
            final.setdefault(rid, {})[c] = (sig, max(cand, key=lambda x: x[1])[2])
    return final


def _f1_comentarios(pred, gold, ids):
    tp = tpd = npred = ngold = 0
    for rid in ids:
        p, g = pred.get(rid, {}), gold.get(rid, {})
        tp += sum(1 for c, (s, _) in g.items() if c in p and p[c][0] == s)
        tpd += sum(1 for c in g if c in p)
        npred += len(p)
        ngold += len(g)
    f = lambda x: 2 * x / (npred + ngold) if npred + ngold else 0.0
    return f(tp), f(tpd)


def _silver():
    s = pd.read_csv("data/silver/silver_oraciones.csv")
    prof = pd.read_csv("data/review.csv", usecols=["review_id", "profesor_id"]).set_index("review_id").profesor_id
    s["profesor_id"] = s.review_id.map(prof)
    gold = {}                                   # etiquetas del silver consolidadas al comentario (para validar)
    for rid, g in s.groupby("review_id"):
        et = [[c + SIG[v] for c in COD if (v := r[c])] for _, r in g.iterrows()]
        gold[rid] = {c: (sig, 0) for c, (sig, _) in _consolidar_tokens(et).items()}
    return s, gold


def _consolidar_tokens(etiquetas):
    por = {}
    for k, toks in enumerate(etiquetas):
        for tk in toks:
            por.setdefault(tk[:3], []).append(tk[3])
    out = {}
    for c, lst in por.items():
        pos, neg = "+" in lst, "-" in lst
        out[c] = ("0" if pos == neg else ("+" if pos else "-"), 0)
    return out


def cmd_entrenar(a):
    DIR.mkdir(parents=True, exist_ok=True)
    s, gold = _silver()
    cache = DIR / "emb_silver.npy"
    if cache.exists() and len(np.load(cache)) == len(s):
        X = np.load(cache)
    else:
        print(f"Codificando {len(s):,} oraciones con {EMB} (CPU)...")
        X = _codificar(s.oracion)
        np.save(cache, X)
    profs = np.array(sorted(s.profesor_id.unique()))
    rng = np.random.default_rng(SEMILLA)
    val_profs = set(rng.choice(profs, int(round(0.10 * len(profs))), replace=False))
    es_val = s.profesor_id.isin(val_profs).values
    ids_val = sorted(set(s.review_id[es_val]))
    print(f"Entrenamiento: {(~es_val).sum():,} oraciones · validación interna: {es_val.sum():,} oraciones "
          f"({len(ids_val)} comentarios, {len(val_profs)} profesores)")
    mejor = None
    for C in a.Cs:
        modelos = {c: LogisticRegression(C=C, class_weight="balanced", max_iter=3000).fit(X[~es_val], s.loc[~es_val, c]) for c in COD}
        P = _probs(modelos, X[es_val])
        ids_filas = s.review_id[es_val].tolist()
        for t in np.round(np.concatenate([np.arange(0.30, 0.90, 0.05), np.arange(0.90, 0.995, 0.01)]), 2):
            fp, fd = _f1_comentarios(_consolidar(ids_filas, P, t), gold, ids_val)
            if mejor is None or fp > mejor[0]:
                mejor = (fp, fd, C, float(t))
        print(f"  C={C}: mejor hasta ahora F1 aspecto+pol={mejor[0]:.3f} (det {mejor[1]:.3f}) con C={mejor[2]}, t={mejor[3]}")
    fp, fd, C, t = mejor
    print(f"Elegido en validación interna del silver: C={C}, t={t} -> F1 aspecto+pol {fp:.3f}, detección {fd:.3f}")
    modelos = {c: LogisticRegression(C=C, class_weight="balanced", max_iter=3000).fit(X, s[c]) for c in COD}
    joblib.dump(modelos, DIR / "modelos.joblib")
    cfg = dict(version=VERSION, embedding=EMB, C=C, t=t, semilla=SEMILLA, n_oraciones=len(s), n_comentarios=int(s.review_id.nunique()),
               val_f1_pol=round(fp, 4), val_f1_det=round(fd, 4), silver_prompt=sorted(s.prompt.unique()), fecha=datetime.now().isoformat(timespec="seconds"))
    (DIR / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en {DIR} (reentrenado con todo el silver).")
    return 0


def cmd_predecir(a):
    modelos = joblib.load(DIR / "modelos.joblib")
    cfg = json.loads((DIR / "config.json").read_text(encoding="utf-8"))
    rev = A._comentarios_reales("data/review.csv")
    if a.conjunto == "dev":
        g = pd.read_csv("data/gold_para_anotar.csv", encoding="utf-8-sig")
        rev = rev[rev.review_id.isin(g[g.conjunto == "dev"].review_id)]
        salida = DIR / "review_aspecto_v2a_dev.csv"
    else:
        salida = Path("data/review_aspecto_v2a.csv")
    masc = A._mascaras("data/profesor.csv")
    ids, orig, enm = [], [], []
    for rid, pid, texto in zip(rev.review_id, rev.profesor_id, rev.comentario):
        for i, f in A.frases(texto):
            o = texto[i:f].strip()
            ids.append(int(rid)); orig.append(o); enm.append(masc[pid](o))
    print(f"{len(rev):,} comentarios -> {len(ids):,} oraciones; codificando...")
    P = _probs(modelos, _codificar(enm))
    final = _consolidar(ids, P, cfg["t"])
    filas = []
    for rid, asp in final.items():
        for c in COD:
            if c in asp:
                sig, k = asp[c]
                ev = orig[k][:280].rsplit(" ", 1)[0] if len(orig[k]) > 280 else orig[k]
                filas.append((rid, A.CODIGOS[c], A.POL[sig], ev, cfg["version"]))
    out = pd.DataFrame(filas, columns=["review_id", "aspecto", "polaridad", "evidencia", "version_modelo"])
    out.insert(0, "review_aspecto_id", range(1, len(out) + 1))
    out.to_csv(salida, index=False, encoding="utf-8")
    print(f"{len(out):,} filas en {salida} (umbral t={cfg['t']})")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("entrenar"); p.add_argument("--Cs", type=float, nargs="+", default=[0.5, 1.0, 2.0])
    p = sub.add_parser("predecir"); p.add_argument("--conjunto", choices=["dev", "todos"], default="dev")
    a = ap.parse_args()
    sys.exit({"entrenar": cmd_entrenar, "predecir": cmd_predecir}[a.cmd](a))
