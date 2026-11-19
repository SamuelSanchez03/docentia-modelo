#!/usr/bin/env python3
"""
generar_silver.py - Etiquetas automáticas («silver») por oración con Claude Code en modo no interactivo (`claude -p`).

Con la sesión de Claude Code iniciada con un plan Pro/Max, `claude -p` consume los límites de uso del plan (no se cobra
como API). NO definas ANTHROPIC_API_KEY: si existe, la CLI la usaría y se cobraría como API (el script se niega).

Comandos (desde la carpeta del proyecto):
  python generar_silver.py muestra                         # elige los comentarios del silver (solo profesores de entrenamiento)
  python generar_silver.py etiquetar --conjunto dev        # control de calidad: etiqueta los 99 comentarios de dev del gold
  python generar_silver.py etiquetar --n 100               # etiqueta los primeros 100 de la muestra (reanudable)
  python generar_silver.py uso                             # resume tokens, tiempo y costo equivalente registrados
  python generar_silver.py exportar --conjunto dev         # -> data/silver/review_aspecto_silver_dev.csv (para evaluar)
  python generar_silver.py exportar                        # -> data/silver/silver_oraciones.csv (para entrenar)

Reglas: las oraciones salen de absa_baseline.frases() y se enmascaran con crear_mascara() (mismo preprocesamiento que el
modelo final). La evidencia exportada es la oración ORIGINAL (subcadena exacta). El silver solo entrena; nunca mide (D2.3).
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import absa_baseline as A

DIR = Path("data/silver")
PROMPT = Path("silver/prompt_v1.md")
CLAUDE = os.environ.get("CLAUDE_BIN") or str(Path.home() / ".local/bin/claude")
SEMILLA = 42
SIGNO = {"+": 1, "-": 2, "0": 3}            # 0 = no_menciona (columnas de silver_oraciones.csv)
TOKEN = re.compile(r"^(RET|CLA|CAL|ACC|CAR|RIG|ORG|CLI|ASI)([+\-0])$")


def _version_prompt():
    return f"{PROMPT.stem}-{hashlib.sha256(PROMPT.read_bytes()).hexdigest()[:8]}"


# ---------------------------------------------------------------- muestra
def cmd_muestra(a):
    salida = DIR / "muestra.csv"
    if salida.exists() and not a.forzar:
        sys.exit(f"{salida} ya existe; no se sobrescribe (usa --forzar para rehacerla).")
    rev = A._comentarios_reales("data/review.csv")
    part = pd.read_csv("data/particion_profesor.csv")
    rev = rev.merge(part, on="profesor_id")
    tr = rev[rev.conjunto == "entrenamiento"]
    gold = set(pd.read_csv("data/gold_para_anotar.csv", encoding="utf-8-sig").review_id)
    assert not (gold & set(tr.review_id)), "fuga: hay comentarios del gold entre los de entrenamiento"
    v0 = pd.read_csv("data/review_aspecto.csv")
    raros = set(v0[v0.aspecto.isin(["Retroalimentación", "Organización / proyectos"])].review_id) & set(tr.review_id)
    rng = np.random.default_rng(SEMILLA)
    ids_raros = sorted(raros)
    sel_raros = list(rng.choice(ids_raros, min(a.n_raros, len(ids_raros)), replace=False))
    resto = sorted(set(tr.review_id) - set(sel_raros))
    sel_azar = list(rng.choice(resto, a.n - len(sel_raros), replace=False))
    filas = [(int(i), "azar") for i in sel_azar] + [(int(i), "raro_RET_ORG") for i in sel_raros]
    orden = rng.permutation(len(filas))               # mezcla: cualquier prefijo es una muestra representativa
    out = pd.DataFrame([filas[i] for i in orden], columns=["review_id", "origen"])
    DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(salida, index=False)
    print(f"{len(out)} comentarios -> {salida} ({(out.origen == 'azar').sum()} al azar, {(out.origen != 'azar').sum()} con RET/ORG según v0)")
    return 0


# ---------------------------------------------------------------- preparación de oraciones
def _comentarios(conjunto):
    rev = pd.read_csv("data/review.csv", usecols=["review_id", "profesor_id", "comentario"]).set_index("review_id")
    if conjunto == "dev":
        g = pd.read_csv("data/gold_para_anotar.csv", encoding="utf-8-sig")
        ids = [int(i) for i in g[g.conjunto == "dev"].review_id]
    else:
        ids = [int(i) for i in pd.read_csv(DIR / "muestra.csv").review_id]
    masc = A._mascaras("data/profesor.csv")
    out = []
    for rid in ids:
        texto = rev.at[rid, "comentario"]
        m = masc[rev.at[rid, "profesor_id"]]
        oraciones = [texto[i:f].strip() for i, f in A.frases(texto)]
        out.append({"id": rid, "originales": oraciones, "enmascaradas": [m(o) for o in oraciones]})
    return out


def _mensaje(lote):
    partes = ["Annotate these reviews."]
    for c in lote:
        partes.append(f'\nReview id "{c["id"]}":')
        partes += [f"{k}. {o}" for k, o in enumerate(c["enmascaradas"], 1)]
    return "\n".join(partes)


def _validar(lote, texto):
    """dict id -> lista (por oración) de listas de tokens; lanza ValueError si no cumple el formato."""
    ini, fin = texto.find("{"), texto.rfind("}")
    datos = json.loads(texto[ini:fin + 1])
    por_id = {str(c["id"]): c for c in datos["comentarios"]}
    res = {}
    for c in lote:
        d = por_id.get(str(c["id"]))
        if d is None:
            raise ValueError(f"falta el comentario {c['id']}")
        n = len(c["enmascaradas"])
        ors = {int(o["n"]): o.get("etiquetas", []) for o in d["oraciones"]}
        # una «oración» sin letras ni dígitos (p. ej. «)») puede omitirse: no tiene aspectos
        for k in range(1, n + 1):
            if k not in ors and not re.search(r"[A-Za-z0-9]", c["enmascaradas"][k - 1]):
                ors[k] = []
        if set(ors) != set(range(1, n + 1)):
            raise ValueError(f"comentario {c['id']}: oraciones {sorted(ors)} != 1..{n}")
        etiquetas = []
        for k in range(1, n + 1):
            toks = [t.strip() for t in ors[k]]
            if not all(TOKEN.match(t) for t in toks):
                raise ValueError(f"comentario {c['id']} oración {k}: etiquetas inválidas {toks}")
            # Un aspecto repetido con signos distintos en la misma oración se combina con la regla M2.2/D3
            # (+ y - -> 0; un signo con 0 -> el signo), en vez de descartar el lote.
            por = {}
            for t in toks:
                por.setdefault(t[:3], set()).add(t[3])
            unidos = []
            for cod in dict.fromkeys(t[:3] for t in toks):
                s = por[cod]
                unidos.append(cod + ("0" if {"+", "-"} <= s else "+" if "+" in s else "-" if "-" in s else "0"))
            etiquetas.append(unidos)
        res[str(c["id"])] = etiquetas
    return res


# ---------------------------------------------------------------- llamada a claude -p
def _llamar(mensaje, modelo):
    if os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY está definida: claude -p se cobraría como API. Quítala para usar tu plan.")
    cmd = [CLAUDE, "-p", "--model", modelo, "--tools", "", "--system-prompt", PROMPT.read_text(encoding="utf-8"),
           "--output-format", "json", "--no-session-persistence", "--strict-mcp-config"]
    with tempfile.TemporaryDirectory() as vacio:           # carpeta vacía: sin CLAUDE.md ni contexto del proyecto
        t0 = time.time()
        p = subprocess.run(cmd, input=mensaje, capture_output=True, text=True, cwd=vacio, timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f"claude -p salió con {p.returncode}: {p.stderr.strip()[:500] or p.stdout.strip()[:500]}")
    salida = json.loads(p.stdout)
    if salida.get("is_error"):
        raise RuntimeError(f"claude -p devolvió error: {str(salida.get('result'))[:500]}")
    return salida, time.time() - t0


def _registrar_uso(conjunto, modelo, n, salida, segundos, ok):
    ruta = DIR / "uso.csv"
    nuevo = not ruta.exists()
    u = salida.get("usage", {}) or {}
    with ruta.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "conjunto", "modelo", "prompt", "n_comentarios", "ok", "input_tokens", "output_tokens",
                        "cache_creation_input_tokens", "cache_read_input_tokens", "segundos", "costo_equivalente_usd"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), conjunto, modelo, _version_prompt(), n, int(ok),
                    u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cache_creation_input_tokens", 0),
                    u.get("cache_read_input_tokens", 0), round(segundos, 1), salida.get("total_cost_usd", "")])


def cmd_etiquetar(a):
    if a.conjunto == "entrenamiento" and not (DIR / "muestra.csv").exists():
        sys.exit("Primero: python generar_silver.py muestra")
    crudo = DIR / f"crudo_{a.conjunto}_{a.modelo}.jsonl"
    hechos = set()
    if crudo.exists():
        for l in crudo.read_text(encoding="utf-8").splitlines():
            hechos |= set(json.loads(l)["etiquetas"])
    coms = [c for c in _comentarios(a.conjunto) if str(c["id"]) not in hechos]
    if a.n:
        objetivo = a.n - len(hechos)
        coms = coms[:max(0, objetivo)]
    if not coms:
        print(f"Nada por etiquetar ({len(hechos)} ya en {crudo}).")
        return 0
    print(f"Etiquetando {len(coms)} comentarios ({a.conjunto}) en lotes de {a.lote} con '{a.modelo}'; ya hechos: {len(hechos)}")
    for i in range(0, len(coms), a.lote):
        lote = coms[i:i + a.lote]
        res = None
        for intento in (1, 2):
            try:
                salida, seg = _llamar(_mensaje(lote), a.modelo)
            except RuntimeError as e:
                print(f"  lote {i // a.lote + 1}: {e}")
                if "limit" in str(e).lower():
                    sys.exit("Parece un límite de uso del plan: el avance quedó guardado; vuelve a correr más tarde.")
                continue
            try:
                res = _validar(lote, salida.get("result", ""))
                _registrar_uso(a.conjunto, a.modelo, len(lote), salida, seg, True)
                break
            except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
                _registrar_uso(a.conjunto, a.modelo, len(lote), salida, seg, False)
                print(f"  lote {i // a.lote + 1}, intento {intento}: formato inválido ({e})")
        if res is None:
            print(f"  lote {i // a.lote + 1} descartado tras 2 intentos ({[c['id'] for c in lote]})")
            continue
        with crudo.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"fecha": datetime.now().isoformat(timespec="seconds"), "modelo": a.modelo,
                                "prompt": _version_prompt(), "etiquetas": res}, ensure_ascii=False) + "\n")
        u = salida.get("usage", {}) or {}
        print(f"  lote {i // a.lote + 1}: {len(lote)} comentarios · {seg:.0f}s · in {u.get('input_tokens', 0)}+{u.get('cache_read_input_tokens', 0)}(cache) / out {u.get('output_tokens', 0)} tokens")
    return 0


# ---------------------------------------------------------------- uso
def cmd_uso(a):
    d = pd.read_csv(DIR / "uso.csv")
    d["entrada"] = d.input_tokens + d.cache_creation_input_tokens + d.cache_read_input_tokens
    g = d.groupby(["conjunto", "modelo"]).agg(llamadas=("ok", "size"), validas=("ok", "sum"), comentarios=("n_comentarios", "sum"),
                                              entrada=("entrada", "sum"), salida=("output_tokens", "sum"),
                                              segundos=("segundos", "sum"), costo_eq=("costo_equivalente_usd", "sum"))
    g["entrada_por_com"] = (g.entrada / g.comentarios).round(0)
    g["salida_por_com"] = (g.salida / g.comentarios).round(0)
    g["seg_por_com"] = (g.segundos / g.comentarios).round(1)
    print(g.to_string())
    print("\n'costo_eq' es lo que costaría como API; con tu plan no se cobra, pero sirve para comparar el consumo entre modelos.")
    return 0


# ---------------------------------------------------------------- exportar
def _consolidar(etiquetas):
    """Por comentario: {codigo: (signo, indice_oracion_evidencia)} con la regla M2.2."""
    por = {}
    for k, toks in enumerate(etiquetas):
        for t in toks:
            por.setdefault(t[:3], []).append((t[3], k))
    res = {}
    for cod, lst in por.items():
        pos = any(s == "+" for s, _ in lst)
        neg = any(s == "-" for s, _ in lst)
        sig = "0" if pos == neg else ("+" if pos else "-")
        k = next((k for s, k in lst if s == sig), lst[0][1])
        res[cod] = (sig, k)
    return res


def cmd_exportar(a):
    filas = {}
    for crudo in sorted(DIR.glob(f"crudo_{a.conjunto}_*.jsonl")):
        if a.modelo and not crudo.stem.endswith("_" + a.modelo):
            continue
        for l in crudo.read_text(encoding="utf-8").splitlines():
            d = json.loads(l)
            for rid, et in d["etiquetas"].items():
                filas[int(rid)] = (et, d["modelo"], d["prompt"])
    if not filas:
        sys.exit("No hay nada etiquetado para ese conjunto.")
    coms = {c["id"]: c for c in _comentarios(a.conjunto)}
    if a.conjunto == "dev":                                   # formato review_aspecto, para `absa_baseline.py evaluar`
        out = []
        for rid, (et, modelo, prompt) in filas.items():
            for cod, (sig, k) in _consolidar(et).items():
                ev = coms[rid]["originales"][k]
                ev = ev[:280].rsplit(" ", 1)[0] if len(ev) > 280 else ev
                out.append((rid, A.CODIGOS[cod], A.POL[sig], ev, f"silver-{modelo}-{prompt}"))
        df = pd.DataFrame(out, columns=["review_id", "aspecto", "polaridad", "evidencia", "version_modelo"])
        df.insert(0, "review_aspecto_id", range(1, len(df) + 1))
        ruta = DIR / "review_aspecto_silver_dev.csv"
    else:                                                     # una fila por oración, 9 columnas 0..3
        out = []
        for rid, (et, modelo, prompt) in filas.items():
            for k, toks in enumerate(et):
                fila = {"review_id": rid, "oracion_idx": k, "oracion": coms[rid]["enmascaradas"][k], "modelo": modelo, "prompt": prompt}
                fila.update({c: 0 for c in A.CODIGOS})
                fila.update({t[:3]: SIGNO[t[3]] for t in toks})
                out.append(fila)
        df = pd.DataFrame(out)
        ruta = DIR / "silver_oraciones.csv"
    df.to_csv(ruta, index=False, encoding="utf-8")
    print(f"{len(filas)} comentarios -> {len(df)} filas en {ruta}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("muestra"); p.add_argument("--n", type=int, default=4000); p.add_argument("--n-raros", type=int, default=1000)
    p.add_argument("--forzar", action="store_true")
    p = sub.add_parser("etiquetar"); p.add_argument("--conjunto", choices=["entrenamiento", "dev"], default="entrenamiento")
    p.add_argument("--n", type=int, default=0, help="total deseado (incluye lo ya hecho); 0 = todos")
    p.add_argument("--lote", type=int, default=20); p.add_argument("--modelo", default="sonnet")
    sub.add_parser("uso")
    p = sub.add_parser("exportar"); p.add_argument("--conjunto", choices=["entrenamiento", "dev"], default="entrenamiento")
    p.add_argument("--modelo")
    a = ap.parse_args()
    sys.exit({"muestra": cmd_muestra, "etiquetar": cmd_etiquetar, "uso": cmd_uso, "exportar": cmd_exportar}[a.cmd](a))
