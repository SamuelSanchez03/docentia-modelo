#!/usr/bin/env python3
"""
absa_baseline.py - Línea base de ABSA (aspectos + polaridad) para los comentarios de review.csv.

Tres comandos:
  1) muestra   -> genera gold_para_anotar.csv (comentarios que anotas A MANO para medir F1)
  2) etiquetar -> escribe review_aspecto.csv (mismo formato que usará el modelo final)
  3) evaluar   -> compara review_aspecto.csv contra tu gold anotado (precisión, recall, F1)

Uso:
  python absa_baseline.py muestra   --review data/review.csv --n 300
  python absa_baseline.py etiquetar --review data/review.csv --salida data/review_aspecto.csv
  python absa_baseline.py etiquetar --review data/review.csv --polaridad hf     # opcional (ver abajo)
  python absa_baseline.py evaluar   --gold gold_anotado.csv --pred data/review_aspecto.csv

Anotación del gold (columna 'anotacion'): código del aspecto + polaridad, separados por espacio.
  Polaridad: + positivo | - negativo | 0 mixto/neutro (el aspecto se menciona sin juicio claro)
  Ejemplo: "CAL+ RIG0 CLI+"      (vacío = ningún aspecto)
  Códigos: RET Retroalimentación | CLA Claridad de evaluación | CAL Calidad de clase |
           ACC Accesibilidad y trato | CAR Carga de trabajo | RIG Rigor de calificación |
           ORG Organización / proyectos | CLI Clima de aula | ASI Asistencia / formato

Reglas de diseño: la evidencia es un fragmento EXACTO del comentario original; la estrella
del alumno NO se usa para decidir la polaridad; "Rigor" (hard/easy) es neutro por sí mismo: solo
es positivo/negativo si el texto lo califica (fair, worth it / unfair, nothing like the notes).

--polaridad hf usa un modelo preentrenado de sentimiento (cardiffnlp/twitter-roberta-base-sentiment-latest)
sobre cada cláusula; requiere `pip install transformers torch` y se descarga la primera vez.
"""
import argparse
import re
from pathlib import Path

import pandas as pd

VERSION = "reglas-v0.1"
CODIGOS = {
    "RET": "Retroalimentación", "CLA": "Claridad de evaluación", "CAL": "Calidad de clase",
    "ACC": "Accesibilidad y trato", "CAR": "Carga de trabajo", "RIG": "Rigor de calificación",
    "ORG": "Organización / proyectos", "CLI": "Clima de aula", "ASI": "Asistencia / formato",
}
POL = {"+": "positivo", "-": "negativo", "0": "mixto_neutro"}


def rx(s):
    return re.compile(s, re.I) if s else None


# solo_cues=True: la polaridad sale únicamente de las frases-señal (no del sentimiento general),
# para que "hard" o "lots of homework" no se confundan con "mal profesor".
ASPECTOS = {
    "RET": dict(solo=False,
        patron=rx(r"\bfeedback\b|\bcomments? on (?:our |my |the )?(?:papers?|work|essays?|assignments?)|\b(?:returns?|returned|grad(?:es|ed|ing)) (?:\w+ ){0,2}(?:quickly|fast|promptly|late|slowly)|\b(?:responds?|replies|replied|answers?) (?:\w+ ){0,2}(?:e-?mails?|questions?)|\be-?mails? (?:back|response)"),
        pos=rx(r"\b(?:good|great|helpful|useful|detailed|quick(?:ly)?|fast|prompt(?:ly)?|constructive|thorough)\b"),
        neg=rx(r"\bno (?:feedback|comments?|responses?)\b|\b(?:never|barely|rarely|slow(?:ly)?|late|useless|vague|unhelpful)\b")),
    "CLA": dict(solo=False,
        patron=rx(r"\brubrics?\b|\bgrading (?:criteria|scale|policy|system)|\b(?:clear|unclear|vague|confusing) (?:grading|expectations|instructions|directions)|\bexpectations\b|\bsyllabus\b|\b(?:exams?|tests?|quizz?es) (?:are|were|is|was) (?:fair|unfair|clear|based on|nothing like|not (?:based|related))|\bgrad(?:es|ed|ing) (?:is |are |was |were )?(?:fair|unfair|clear|unclear|fairly|unfairly)|\bfair(?:ly)? grad(?:er|ing)"),
        pos=rx(r"\b(?:clear|clearly|fair|fairly|straightforward|specific|detailed|based on)\b"),
        neg=rx(r"\b(?:unclear|vague|confusing|unfair|unfairly|arbitrary|random|nothing like|trick(?:y)?)\b")),
    "CAL": dict(solo=False, pos=None, neg=None,
        patron=rx(r"\blectures?\b|\bexplain(?:s|ed|ing)?\b|\bexplanations?\b|\bteach(?:es|ing)?\b|\btaught\b|\bknowledgeable\b|\bengaging\b|\bboring\b|\bconfus(?:ing|ed)\b|\binteresting\b|\bcontent\b|\bmaterials?\b|\bclass(?:es)? (?:is|was|were|are)\b|\bslides\b|\blearn(?:ed|ing)?\b")),
    "ACC": dict(solo=False, pos=None, neg=None,
        patron=rx(r"\boffice hours?\b|\bavailable\b|\bapproachable\b|\bunapproachable\b|\baccessible\b|\bhelpful\b|\bhelps? (?:you|students|us|me)\b|\bcar(?:es|ing)\b|\bkind\b|\bnice\b|\bsweet\b|\brude\b|\bunderstanding\b|\bpatient\b|\bwill(?: always)? (?:help|meet)\b|\bwilling to help\b")),
    "CAR": dict(solo=True,
        patron=rx(r"\bhomework\b|\bworkload\b|\bassignments?\b|\bbusy ?work\b|\b(?:so|too) much (?:work|reading|homework)\b|\blots? of (?:work|reading|papers|essays|homework)\b|\btons? of (?:work|reading|homework)\b|\breading load\b"),
        pos=rx(r"\bno (?:homework|work|busy ?work)\b|\blight\b|\bnot (?:much|too much|too heavy|too bad)\b|\bmanageable\b|\breasonable\b|\bminimal\b|\bfew assignments\b"),
        neg=rx(r"\b(?:too|so) much\b|\blots? of\b|\ba lot of\b|\ba ton\b|\btons? of\b|\bheavy\b|\boverwhelming\b|\bendless\b|\bnonstop\b")),
    "RIG": dict(solo=True,
        patron=rx(r"\bhard\b|\btough\b|\bdifficult\b|\bchalleng(?:e|es|ing)\b|\bdemanding\b|\bstrict\b|\bharsh\b|\brigorous\b|\beasy\b|\beasier\b|\bgrader\b|\bhigh standards\b|\bexpects? a lot\b|\bimpossible\b|\bunfair(?:ly)?\b|\btrick(?:y| questions?)\b|\bnothing like\b"),
        pos=rx(r"\bfair(?:ly)?\b|\bworth\b|\brewarding\b|\bprepared?\b|\bbut (?:you )?learn\b|\blearn(?:ed)? (?:a lot|so much)\b"),
        neg=rx(r"\bunfair(?:ly)?\b|\bimpossible\b|\bharsh\b|\btrick(?:y| questions?)\b|\bnothing like\b|\bbrutal\b|\bridiculous\b|\bunreasonable\b|\bunrealistic\b")),
    "ORG": dict(solo=False,
        patron=rx(r"\bgroup projects?\b|\bteam projects?\b|\bprojects?\b|\borgani[sz]ed\b|\b(?:dis|un)organi[sz]ed\b|\bdeadlines?\b|\bschedule\b|\bchaotic\b|\ball over the place\b|\blast[- ]minute\b"),
        pos=rx(r"\borgani[sz]ed\b|\bstructured\b"),
        neg=rx(r"\b(?:dis|un)organi[sz]ed\b|\bchaotic\b|\ball over the place\b|\blast[- ]minute\b")),
    "CLI": dict(solo=False, pos=None, neg=None,
        patron=rx(r"\bfunny\b|\bhilarious\b|\bhumou?r\b|\brespect(?:ful|s|ed)?\b|\bdisrespect(?:ful)?\b|\binspir\w*|\bpassion(?:ate)?\b|\benthusias\w*|\benergy\b|\batmosphere\b|\bcondescending\b|\bsarcastic\b|\bfriendly\b|\bwelcoming\b|\bhostile\b|\brude\b|\bentertaining\b|\bfun\b")),
    "ASI": dict(solo=True,
        patron=rx(r"\battendance\b|\bmandatory\b|\bskip(?:ping)? class\b|\bpop quizz?es\b|\bquizz?es\b|\bextra credit\b|\bparticipat\w*|\bonline\b|\bzoom\b|\bin[- ]person\b|\bdrops? (?:your |the )?lowest\b|\blate (?:work|policy)\b"),
        pos=rx(r"\bextra credit\b|\boptional\b|\bdrops? (?:your |the )?lowest\b|\bflexible\b|\bno attendance\b|\bnot (?:mandatory|required)\b"),
        neg=rx(r"\bpop quizz?es\b|\bsurprise quizz?es\b|\bbeware\b|\bstrict (?:attendance|late)\b")),
}

POS = set("""great good best amazing awesome excellent love loved loves helpful nice kind funny hilarious engaging
interesting clear fair caring passionate inspiring inspirational inspired knowledgeable enjoy enjoyed enjoyable fantastic
wonderful recommend recommended organized patient understanding friendly stimulating favorite brilliant perfect effective
respectful approachable available accessible informative entertaining fun worth sweet welcoming""".split())
NEG = set("""bad worst terrible awful horrible boring confusing confused unclear unfair rude mean avoid hate hated useless
waste disorganized unorganized unhelpful condescending arrogant lazy pointless annoying frustrating disrespectful dull
vague impossible ridiculous unprofessional poor worse sucks stupid dreadful harsh sarcastic hostile unapproachable""".split())
NEGADORES = {"not", "no", "never", "without", "hardly", "barely", "cannot"}
TOKEN = re.compile(r"[a-z']+")


def _negado(texto, pos_ini):
    previos = TOKEN.findall(texto[:pos_ini].lower())[-3:]
    return any(t in NEGADORES or t.endswith("n't") for t in previos)


def _signo_cues(texto, pos_rx, neg_rx):
    """+1/-1/0 según frases-señal; una señal precedida por negación invierte su signo."""
    s = 0
    for rgx, base in ((pos_rx, 1), (neg_rx, -1)):
        if rgx is None:
            continue
        for m in rgx.finditer(texto):
            s += -base if _negado(texto, m.start()) else base
    return (s > 0) - (s < 0)


def _signo_lexico(texto):
    s = 0
    low = texto.lower()
    toks = [(m.group(0), m.start()) for m in TOKEN.finditer(low)]
    for i, (t, ini) in enumerate(toks):
        base = 1 if t in POS else -1 if t in NEG else 0
        if base:
            previos = [x[0] for x in toks[max(0, i - 3):i]]
            neg = any(p in NEGADORES or p.endswith("n't") for p in previos)
            s += -base if neg else base
    return (s > 0) - (s < 0)


_hf = None


def _signos_hf(clausulas):
    global _hf
    if _hf is None:
        from transformers import pipeline  # import perezoso: solo si se pide --polaridad hf
        _hf = pipeline("text-classification", model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                       truncation=True, max_length=128, batch_size=32)
    unicas = sorted(set(clausulas))
    out = _hf(unicas)
    mapa = {"positive": 1, "negative": -1, "neutral": 0}
    return {c: mapa[r["label"].lower()] for c, r in zip(unicas, out)}


def frases(texto):
    """(inicio, fin) de cada oración en el texto ORIGINAL (para que la evidencia sea un fragmento exacto)."""
    return [(m.start(), m.end()) for m in re.finditer(r"[^.!?\n]+[.!?]*", texto) if m.group(0).strip()]


SPLIT = re.compile(r"\b(?:but|however|although|though|yet)\b", re.I)


def detectar(texto):
    """Lista de (codigo, frase, clausula) por cada aspecto mencionado."""
    hallazgos = []
    for ini, fin in frases(texto):
        frase = texto[ini:fin].strip()
        for cod, cfg in ASPECTOS.items():
            for cl in SPLIT.split(frase):
                if cfg["patron"].search(cl):
                    hallazgos.append((cod, frase, cl))   # una entrada por cláusula que menciona el aspecto
    return hallazgos


def etiquetar_texto(texto, base_fn, hf_map=None):
    por_aspecto = {}
    for cod, frase, cl in detectar(texto):
        cfg = ASPECTOS[cod]
        s = _signo_cues(frase, cfg["pos"], cfg["neg"])          # señales sobre la oración completa
        if s == 0 and not cfg["solo"]:
            s = hf_map[cl] if hf_map is not None else base_fn(cl)  # sentimiento general sobre la cláusula
        por_aspecto.setdefault(cod, []).append((s, frase[:280].rsplit(" ", 1)[0] if len(frase) > 280 else frase))
    filas = []
    for cod, lst in por_aspecto.items():
        pos = any(s > 0 for s, _ in lst)
        neg = any(s < 0 for s, _ in lst)
        pol = "mixto_neutro" if pos == neg else ("positivo" if pos else "negativo")
        objetivo = {"positivo": 1, "negativo": -1}.get(pol)
        evidencia = next((e for s, e in lst if s == objetivo), lst[0][1])
        filas.append((CODIGOS[cod], pol, evidencia))
    return filas


def cmd_etiquetar(a):
    rev = pd.read_csv(a.review, usecols=["review_id", "comentario"]).dropna(subset=["comentario"])
    hf_map = None
    if a.polaridad == "hf":
        clausulas = [cl for t in rev["comentario"] for c, f, cl in detectar(t) if not ASPECTOS[c]["solo"]]
        hf_map = _signos_hf(clausulas)
    filas = []
    for rid, texto in zip(rev["review_id"], rev["comentario"]):
        for asp, pol, ev in etiquetar_texto(texto, _signo_lexico, hf_map):
            filas.append((rid, asp, pol, ev))
    out = pd.DataFrame(filas, columns=["review_id", "aspecto", "polaridad", "evidencia"])
    out.insert(0, "review_aspecto_id", range(1, len(out) + 1))
    out["version_modelo"] = f"{VERSION}-{a.polaridad}"
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.salida, index=False, encoding="utf-8")
    print(f"{len(rev):,} comentarios -> {len(out):,} filas en {a.salida}")
    print(f"Comentarios con al menos un aspecto: {out['review_id'].nunique() / len(rev):.1%}")
    print(out.pivot_table(index="aspecto", columns="polaridad", values="review_id", aggfunc="count", fill_value=0))


def cmd_muestra(a):
    rev = pd.read_csv(a.review, usecols=["review_id", "comentario", "student_star"]).dropna(subset=["comentario"])
    grupos = [rev[rev.student_star <= 2], rev[(rev.student_star > 2) & (rev.student_star < 4)], rev[rev.student_star >= 4]]
    k = a.n // 3
    mu = pd.concat([g.sample(min(k, len(g)), random_state=42) for g in grupos]).sample(frac=1, random_state=1)
    out = mu[["review_id", "comentario"]].assign(anotacion="")
    out.to_csv(a.salida, index=False, encoding="utf-8")
    print(f"{len(out)} comentarios en {a.salida}. Llena la columna 'anotacion' (ver guía al inicio del script).")


def _parse_gold(texto):
    return {(m.group(1), m.group(2)) for m in re.finditer(r"\b([A-Z]{3})([+\-0])", str(texto)) if m.group(1) in CODIGOS}


def cmd_evaluar(a):
    gold = pd.read_csv(a.gold).fillna({"anotacion": ""})
    pred = pd.read_csv(a.pred)
    inv = {v: k for k, v in CODIGOS.items()}
    pred["cod"] = pred["aspecto"].map(inv)
    pred["pol"] = pred["polaridad"].map({v: k for k, v in POL.items()})
    P = {(r, c): p for r, c, p in zip(pred.review_id, pred.cod, pred.pol)}
    G = {}
    for rid, an in zip(gold.review_id, gold.anotacion):
        for c, p in _parse_gold(an):
            G[(rid, c)] = p
    ids = set(gold.review_id)
    P = {k: v for k, v in P.items() if k[0] in ids}
    print(f"{len(ids)} comentarios anotados | aspectos en gold: {len(G)} | en predicción: {len(P)}\n")
    print(f"{'aspecto':28s} {'prec':>6s} {'recall':>7s} {'F1':>6s} {'pol.ok':>7s} {'n_gold':>7s}")
    f1s, TP, FP, FN, TPpol = [], 0, 0, 0, 0
    for c, nombre in CODIGOS.items():
        g = {k for k in G if k[1] == c}
        p = {k for k in P if k[1] == c}
        tp, fp, fn = len(g & p), len(p - g), len(g - p)
        pr, rc = tp / (tp + fp) if tp + fp else 0, tp / (tp + fn) if tp + fn else 0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0
        ok = sum(1 for k in g & p if G[k] == P[k])
        print(f"{nombre:28s} {pr:6.2f} {rc:7.2f} {f1:6.2f} {ok / tp if tp else 0:7.2f} {len(g):7d}")
        if g:
            f1s.append(f1)
        TP, FP, FN, TPpol = TP + tp, FP + fp, FN + fn, TPpol + ok
    pr, rc = TP / (TP + FP) if TP + FP else 0, TP / (TP + FN) if TP + FN else 0
    print(f"\nF1 macro (detección):                {sum(f1s) / len(f1s):.3f}")
    print(f"F1 micro (detección):                {2 * pr * rc / (pr + rc) if pr + rc else 0:.3f}")
    prs, rcs = TPpol / (TP + FP) if TP + FP else 0, TPpol / (TP + FN) if TP + FN else 0
    print(f"F1 micro (aspecto + polaridad):      {2 * prs * rcs / (prs + rcs) if prs + rcs else 0:.3f}   <- el que compara con la meta de 0.85")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("muestra"); m.add_argument("--review", default="data/review.csv")
    m.add_argument("--n", type=int, default=300); m.add_argument("--salida", default="gold_para_anotar.csv")
    e = sub.add_parser("etiquetar"); e.add_argument("--review", default="data/review.csv")
    e.add_argument("--salida", default="data/review_aspecto.csv"); e.add_argument("--polaridad", choices=["lexico", "hf"], default="lexico")
    v = sub.add_parser("evaluar"); v.add_argument("--gold", required=True); v.add_argument("--pred", default="data/review_aspecto.csv")
    args = ap.parse_args()
    {"muestra": cmd_muestra, "etiquetar": cmd_etiquetar, "evaluar": cmd_evaluar}[args.cmd](args)
