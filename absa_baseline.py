#!/usr/bin/env python3
"""
absa_baseline.py v0.2 - Línea base de ABSA (aspectos + polaridad) para los comentarios de review.csv.

Comandos (en el orden en que se usan):
  particion  -> reserva ~15% de profesores (nada de ellos se usa para entrenar); verifica que no cambie
  muestra    -> gold estratificado por estrellas, solo de profesores reservados (dev / test) + doble anotación
  etiquetar  -> escribe review_aspecto.csv (mismo formato que usará el modelo final)
  evaluar    -> F1 contra el gold anotado a mano, con IC 95% bootstrap; candado del conjunto de prueba
  identidad  -> prueba M3.4: cambiar el nombre del profesor no cambia las predicciones
  kappa      -> acuerdo entre dos anotadores (Cohen, 4 clases) y F1 de acuerdo
  registrar  -> fila de modelo_version (solo marca «validado» con F1 >= 0.85 medido en TEST)

Anotación del gold (columna 'anotacion'): código del aspecto + polaridad, separados por espacio.
  Polaridad: + positivo | - negativo | 0 mixto/neutro (el aspecto se menciona sin juicio claro)
  Ejemplo: "CAL+ RIG0 CLI+"    Sin aspecto: escribe "ninguno".   Celda vacía = NO anotado (se ignora).
  Códigos: RET Retroalimentación | CLA Claridad de evaluación | CAL Calidad de clase |
           ACC Accesibilidad y trato | CAR Carga de trabajo | RIG Rigor de calificación |
           ORG Organización / proyectos | CLI Clima de aula | ASI Asistencia / formato

Reglas de diseño: la evidencia es un fragmento EXACTO del comentario original; la estrella del alumno
NO decide aspecto ni polaridad; "Rigor" (hard/easy) es neutro por sí mismo: solo es positivo/negativo si el
texto lo califica (fair, worth it / unfair, impossible). El nombre del profesor se enmascara como [PROF]
antes de detectar (M1.5); la evidencia se toma del texto original.

--polaridad hf usa un modelo preentrenado de sentimiento (cardiffnlp/twitter-roberta-base-sentiment-latest)
sobre cada cláusula; requiere `pip install transformers torch` y se descarga la primera vez.
"""
import argparse
import collections
import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "reglas-v0.2"
VERSION_A2 = "reglas-v0.3"   # v0.2 + reglas de signo del criterio denso para RIG/CAR/ASI (--reglas v0.3)
CODIGOS = {
    "RET": "Retroalimentación", "CLA": "Claridad de evaluación", "CAL": "Calidad de clase",
    "ACC": "Accesibilidad y trato", "CAR": "Carga de trabajo", "RIG": "Rigor de calificación",
    "ORG": "Organización / proyectos", "CLI": "Clima de aula", "ASI": "Asistencia / formato",
}
POL = {"+": "positivo", "-": "negativo", "0": "mixto_neutro"}
META_F1 = 0.85
SEMILLA_PARTICION, SEMILLA_MUESTRA, SEMILLA_MEZCLA, SEMILLA_DOBLE = 42, 42, 1, 7
SEMILLA_BOOTSTRAP, N_BOOTSTRAP = 42, 1000


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
    # "nothing like" ya no está en RIG (doble conteo con Claridad de evaluación, M1.3)
    "RIG": dict(solo=True,
        patron=rx(r"\bhard\b|\btough\b|\bdifficult\b|\bchalleng(?:e|es|ing)\b|\bdemanding\b|\bstrict\b|\bharsh\b|\brigorous\b|\beasy\b|\beasier\b|\bgrader\b|\bhigh standards\b|\bexpects? a lot\b|\bimpossible\b|\bunfair(?:ly)?\b|\btrick(?:y| questions?)\b"),
        pos=rx(r"\bfair(?:ly)?\b|\bworth\b|\brewarding\b|\bprepared?\b|\bbut (?:you )?learn\b|\blearn(?:ed)? (?:a lot|so much)\b"),
        neg=rx(r"\bunfair(?:ly)?\b|\bimpossible\b|\bharsh\b|\btrick(?:y| questions?)\b|\bbrutal\b|\bridiculous\b|\bunreasonable\b|\bunrealistic\b")),
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

# Reglas de signo v0.3 (criterio denso, D7-D9). Escritas a partir del texto de la regla, SIN mirar errores
# de dev. Solo reemplazan las frases-señal (pos/neg) de RIG, CAR y ASI; la detección (patron) es idéntica a v0.2.
# Por defecto, sin señal => 0 (D7: «hard» sin más; D8: cantidad sin adjetivo; D9: quiz regular, asistencia obligatoria, online).
REGLAS_A2 = {
    # D7: + «hard but fair / doable / worth it»; - «unfair / impossible / ridiculous / arbitrary»
    "RIG": (rx(r"\bfair(?:ly)?\b|\bdoable\b|\bworth(?:while)?\b|\brewarding\b|\bprepared?\b|\bmanageable\b|\bbut (?:you )?learn\b|\blearn(?:ed)? (?:a lot|so much)\b"),
            rx(r"\bunfair(?:ly)?\b|\bimpossible\b|\bridiculous\b|\babsurd\b|\barbitrary\b|\bharsh\b|\bbrutal\b|\bunreasonable\b|\bunrealistic\b|\btrick(?:y|s)\b")),
    # D8: - «lots / a lot / too much / every night»; + «not much / light / only two pages»
    "CAR": (rx(r"\bno (?:homework|work|busy ?work|assignments)\b|\blight\b|\bnot (?:much|too much|too heavy|too bad|a lot of)\b|\bmanageable\b|\breasonable\b|\bminimal\b|\b(?:little|few) (?:homework|work|assignments|reading|papers)\b|\bonly (?:a |an )?(?:few|one|two|three|four|five|small|short|\d+)\b"),
            rx(r"\b(?:too|so) much\b|\blots? of\b|\ba lot of\b|\ba ton\b|\btons? of\b|\bheavy\b|\boverwhelming\b|\bendless\b|\bnonstop\b|\bevery (?:night|day)\b|\bhours (?:of|on)\b|\bpiles? up\b|\bmassive\b")),
    # D9: + extra credit / bonus / sin política de asistencia; - quizzes sorpresa / castigo por faltar
    "ASI": (rx(r"\bextra credit\b|\bbonus\b|\boptional\b|\bdrops? (?:your |the )?lowest\b|\bflexible\b|\bno attendance\b|\b(?:doesn'?t|does not|don'?t|do not|never) (?:take|check|require|count) attendance\b|\b(?:don'?t|do not|doesn'?t|does not) (?:need|have) to (?:go|attend|show up|come)\b|\bnot (?:mandatory|required)\b|\battendance (?:is )?(?:optional|not (?:mandatory|required|taken))\b"),
            rx(r"\bpop quizz?es\b|\bsurprise quizz?es\b|\bbeware\b|\bstrict (?:attendance|late)\b")),
}

POS = set("""great good best amazing awesome excellent love loved loves helpful nice kind funny hilarious engaging
interesting clear clearly fair caring passionate inspiring inspirational inspired knowledgeable enjoy enjoyed enjoyable
fantastic wonderful recommend recommended organized patient understanding friendly stimulating favorite brilliant
perfect effective respectful approachable available accessible informative entertaining fun worth sweet welcoming""".split())
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


# ---------------------------------------------------------------- texto: relleno, oraciones, enmascarado
def es_relleno(texto):
    """Nulo, vacío o relleno de la plataforma ('No Comments' / 'No comment', con o sin mayúsculas y puntuación)."""
    if not isinstance(texto, str) or texto.strip() == "":
        return True
    return re.sub(r"[\s.!?]+$", "", texto.strip().lower()) in ("no comments", "no comment")


# Una oración termina en . ! ? o salto de línea, salvo tras abreviaturas (Prof. Dr. Mr. Mrs. Ms. Jr. Sr. St. vs.).
# Los títulos solo cuentan con mayúscula inicial: "a great prof. Very nice" sí corta la oración.
ORACION = re.compile(r"(?:\b(?:Prof|Dr|Mr|Mrs|Ms|Jr|Sr|St)\.|\bvs\.|[^.!?\n])+[.!?]*")


def frases(texto):
    """(inicio, fin) de cada oración en el texto ORIGINAL (para que la evidencia sea un fragmento exacto)."""
    return [(m.start(), m.end()) for m in ORACION.finditer(texto) if m.group(0).strip()]


# Título + apellido. "Professor" solo cuenta sin punto pegado ("the best Professor. Very..." no es un nombre).
TITULO_NOMBRE = re.compile(r"\b(?:(?:Prof|Dr|Mr|Mrs|Ms)\.?|Professor(?![.\w]))\s*[A-Z][A-Za-z\-]+")
MASCARA = "[PROF]"


def _palabra_cargada(tok):
    """True si el token tiene carga para el modelo (léxico de sentimiento o patrón de aspecto)."""
    low = tok.lower()
    if low in POS or low in NEG:
        return True
    return any(c[k] is not None and c[k].search(tok) for c in ASPECTOS.values() for k in ("patron", "pos", "neg"))


def tokens_nombre(nombre):
    """Partes del nombre del profesor (>= 3 letras), tal como están en profesor.csv."""
    return [t for t in re.findall(r"[A-Za-z][A-Za-z'\-]+", str(nombre)) if len(t) >= 3]


def crear_mascara(nombre):
    """Función texto -> texto con [PROF] por el nombre del profesor. Un token con carga (p. ej. el apellido
    'Fair' o 'Sweet') solo se enmascara si va tras un título; el resto, en cualquier posición."""
    libres = [re.escape(t) for t in tokens_nombre(nombre) if not _palabra_cargada(t)]
    rgx = re.compile(r"\b(?:" + "|".join(libres) + r")\b", re.I) if libres else None

    def tras_titulo(m):
        # Limitación conocida (heredada de la v0.2 original, afecta 1 fila: review 7731 «Dr. Sweet's class»):
        # un apellido con carga seguido de posesivo ('s) NO se enmascara y aún dispara el patrón. Corregirlo
        # cambiaría esa fila; se hará en la siguiente iteración de reglas, no en silencio.
        apellido = m.group(0).split()[-1] if m.group(0).split() else ""
        sig = m.string[m.end():m.end() + 1]
        if sig in ("'", "’") and _palabra_cargada(re.split(r"[.\s]", apellido)[-1]):
            return m.group(0)
        return MASCARA

    def mascara(texto):
        t = TITULO_NOMBRE.sub(tras_titulo, texto)
        return rgx.sub(MASCARA, t) if rgx else t
    return mascara


SPLIT = re.compile(r"\b(?:but|however|although|though|yet)\b", re.I)


def detectar(texto, mascara=None):
    """Lista de (codigo, frase_original, clausula_enmascarada, frase_enmascarada) por cada aspecto mencionado."""
    hallazgos = []
    for ini, fin in frases(texto):
        frase = texto[ini:fin].strip()
        masc = mascara(frase) if mascara else frase
        for cod, cfg in ASPECTOS.items():
            for cl in SPLIT.split(masc):
                if cfg["patron"].search(cl):
                    hallazgos.append((cod, frase, cl, masc))   # una entrada por cláusula que menciona el aspecto
    return hallazgos


def etiquetar_texto(texto, base_fn, hf_map=None, mascara=None, reglas=None):
    """[(aspecto, polaridad, evidencia)]. Detección y polaridad sobre el texto enmascarado; evidencia del original."""
    por_aspecto = {}
    for cod, frase, cl, masc in detectar(texto, mascara):
        cfg = ASPECTOS[cod]
        pos_rx, neg_rx = reglas[cod] if reglas and cod in reglas else (cfg["pos"], cfg["neg"])
        s = _signo_cues(masc, pos_rx, neg_rx)                   # señales sobre la oración completa
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


def _mascaras(prof_csv):
    """{profesor_id: función de enmascarado} (se construye una vez por profesor)."""
    prof = pd.read_csv(prof_csv, usecols=["profesor_id", "nombre"])
    return {pid: crear_mascara(n) for pid, n in zip(prof.profesor_id, prof.nombre)}


def _comentarios_reales(review_csv, cols=("review_id", "profesor_id", "comentario")):
    rev = pd.read_csv(review_csv, usecols=list(cols))
    return rev[~rev["comentario"].map(es_relleno)]


# ---------------------------------------------------------------- particion
def _ids_reservados(prof_ids, frac=0.15, semilla=SEMILLA_PARTICION):
    n = int(round(frac * len(prof_ids)))
    return set(np.random.default_rng(semilla).choice(prof_ids, n, replace=False).tolist())


def cmd_particion(a):
    prof = pd.read_csv(a.profesor, usecols=["profesor_id"])
    res = _ids_reservados(prof.profesor_id.values, a.frac, a.semilla)
    nueva = pd.DataFrame({"profesor_id": prof.profesor_id,
                          "conjunto": np.where(prof.profesor_id.isin(res), "reservado", "entrenamiento")})
    salida = Path(a.salida)
    if salida.exists() and not a.forzar:
        vieja = pd.read_csv(salida)
        igual = vieja.equals(nueva)
        print(f"{salida} ya existe y {'COINCIDE' if igual else 'DIFIERE'} con la partición recalculada (semilla {a.semilla}).")
        print("No se sobrescribe: cambiarla invalida el gold (los reservados dejarían de ser reservados). Usa --forzar solo si empiezas de cero.")
        return 0 if igual else 1
    salida.parent.mkdir(parents=True, exist_ok=True)
    nueva.to_csv(salida, index=False, encoding="utf-8")
    rev = _comentarios_reales(a.review).merge(nueva, on="profesor_id")
    print(f"{len(res)} profesores reservados / {len(prof) - len(res)} de entrenamiento -> {salida}")
    print("comentarios con texto real:", rev.conjunto.value_counts().to_dict())
    return 0


# ---------------------------------------------------------------- muestra (gold)
def _construir_gold(review_csv, particion_csv, n, dev_por_estrato, n_doble):
    rev = _comentarios_reales(review_csv, ("review_id", "profesor_id", "comentario", "student_star"))
    part = pd.read_csv(particion_csv)
    pool = rev[rev.profesor_id.isin(set(part[part.conjunto == "reservado"].profesor_id))]
    estratos = [pool[pool.student_star <= 2], pool[(pool.student_star > 2) & (pool.student_star < 4)], pool[pool.student_star >= 4]]
    k = n // 3
    elegidos = []
    for g in estratos:
        s = g.sample(min(k, len(g)), random_state=SEMILLA_MUESTRA)
        elegidos.append(s.assign(conjunto=["dev"] * min(dev_por_estrato, len(s)) + ["test"] * (len(s) - min(dev_por_estrato, len(s)))))
    gold = pd.concat(elegidos).sample(frac=1, random_state=SEMILLA_MEZCLA)
    out = gold[["review_id", "conjunto", "comentario"]].assign(anotacion="")
    doble = out.sample(n_doble, random_state=SEMILLA_DOBLE)[["review_id", "comentario"]].assign(anotacion_2="")
    return out, doble


def cmd_muestra(a):
    gold, doble = _construir_gold(a.review, a.particion, a.n, a.dev_por_estrato, a.n_doble)
    for ruta, nuevo, col in ((Path(a.salida), gold, "anotacion"), (Path(a.salida_doble), doble, "anotacion_2")):
        if ruta.exists() and not a.forzar:
            ex = pd.read_csv(ruta, encoding="utf-8-sig", dtype=str).fillna("")
            mismo = ex.review_id.tolist() == nuevo.review_id.astype(str).tolist()
            llenas = int((ex[col].str.strip() != "").sum())
            print(f"{ruta} ya existe ({len(ex)} filas, {llenas} anotadas): {'misma muestra' if mismo else 'MUESTRA DISTINTA'}. No se sobrescribe.")
        else:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            nuevo.to_csv(ruta, index=False, encoding="utf-8-sig")
            print(f"{len(nuevo)} comentarios en {ruta}. Llena la columna '{col}' (guía al inicio del script).")
    return 0


# ---------------------------------------------------------------- etiquetar
def cmd_etiquetar(a):
    rev = _comentarios_reales(a.review)
    masc = _mascaras(a.profesor)
    hf_map = None
    if a.polaridad == "hf":
        clausulas = [cl for t, p in zip(rev["comentario"], rev["profesor_id"])
                     for c, f, cl, m in detectar(t, masc[p]) if not ASPECTOS[c]["solo"]]
        hf_map = _signos_hf(clausulas)
    filas = []
    for rid, pid, texto in zip(rev["review_id"], rev["profesor_id"], rev["comentario"]):
        for asp, pol, ev in etiquetar_texto(texto, _signo_lexico, hf_map, masc[pid], REGLAS_A2 if a.reglas == "v0.3" else None):
            filas.append((rid, asp, pol, ev))
    out = pd.DataFrame(filas, columns=["review_id", "aspecto", "polaridad", "evidencia"])
    out.insert(0, "review_aspecto_id", range(1, len(out) + 1))
    out["version_modelo"] = f"{VERSION_A2 if a.reglas == 'v0.3' else VERSION}-{a.polaridad}"
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.salida, index=False, encoding="utf-8")
    print(f"{len(rev):,} comentarios con texto real -> {len(out):,} filas en {a.salida}")
    print(f"Comentarios con al menos un aspecto: {out['review_id'].nunique() / len(rev):.1%}")
    print(out.pivot_table(index="aspecto", columns="polaridad", values="review_id", aggfunc="count", fill_value=0))
    return 0


# ---------------------------------------------------------------- anotaciones, métricas
def parse_anotacion(texto):
    """(dict {código: signo} | None si no está anotado, avisos). 'ninguno' -> {}."""
    t = "" if texto is None or (isinstance(texto, float) and np.isnan(texto)) else str(texto).strip()
    if t == "":
        return None, []
    if t.lower() == "ninguno":
        return {}, []
    res, avisos = {}, []
    for tok in t.replace("−", "-").replace("–", "-").split():
        m = re.fullmatch(r"([A-Za-z]{3})([+\-0])", tok)
        if not m or m.group(1).upper() not in CODIGOS:
            avisos.append(f"token inválido '{tok}'")
            continue
        c, p = m.group(1).upper(), m.group(2)
        if c in res and res[c] != p:
            avisos.append(f"{c} con signos contradictorios ('{res[c]}' y '{p}'; se conserva el primero)")
        res.setdefault(c, p)
    return res, avisos


def _f1(tp, n_pred, n_gold):
    if n_pred == 0 or n_gold == 0 or tp == 0:
        return 0.0 if (n_pred or n_gold) else None
    p, r = tp / n_pred, tp / n_gold
    return 2 * p * r / (p + r)


def _conteos(G, P):
    """Por comentario: [tp_pol, tp_det, n_pred, n_gold] (G y P: dict por review_id)."""
    filas = []
    for rid, g in G.items():
        p = P.get(rid, {})
        filas.append([sum(1 for c, s in g.items() if p.get(c) == s), sum(1 for c in g if c in p), len(p), len(g)])
    return np.array(filas, dtype=float)


def _micro(cnt):
    tp_pol, tp_det, n_pred, n_gold = cnt.sum(0)
    return _f1(tp_pol, n_pred, n_gold), _f1(tp_det, n_pred, n_gold)


def _bootstrap(cnt, semilla=SEMILLA_BOOTSTRAP, b=N_BOOTSTRAP):
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(cnt), (b, len(cnt)))
    sumas = cnt[idx].sum(1)
    pol = np.array([_f1(s[0], s[2], s[3]) or 0.0 for s in sumas])
    det = np.array([_f1(s[1], s[2], s[3]) or 0.0 for s in sumas])
    return [float(np.percentile(pol, 2.5)), float(np.percentile(pol, 97.5))], [float(np.percentile(det, 2.5)), float(np.percentile(det, 97.5))]


def _precision_por_signo(G, P, cod):
    """Para las tarjetas (compuerta C): de las veces que el modelo marca cod con + (o -), qué fracción coincide con el gold."""
    out = {}
    for signo, clave in (("+", "pos"), ("-", "neg")):
        marcados = [r for r, d in P.items() if r in G and d.get(cod) == signo]
        ok = sum(1 for r in marcados if G[r].get(cod) == signo)
        out[f"prec_{clave}"] = ok / len(marcados) if marcados else None
        out[f"n_pred_{clave}"] = len(marcados)
    return out


def _sha(ruta, n=12):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()[:n]


def _cargar_pred(ruta, version=None):
    pred = pd.read_csv(ruta)
    versiones = sorted(pred["version_modelo"].unique())
    if version is None and len(versiones) > 1:
        sys.exit(f"{ruta} tiene varias versiones {versiones}: indica una con --version.")
    if version is not None:
        pred = pred[pred.version_modelo == version]
    inv = {v: k for k, v in CODIGOS.items()}
    mapa_pol = {v: k for k, v in POL.items()}
    P = {}
    for rid, asp, pol in zip(pred.review_id, pred.aspecto, pred.polaridad):
        P.setdefault(int(rid), {})[inv[asp]] = mapa_pol[pol]
    return P, (version or versiones[0])


def _cargar_gold(ruta, col="anotacion"):
    gold = pd.read_csv(ruta, encoding="utf-8-sig", dtype={col: str})
    G, avisos, excluidos = {}, [], []
    for i, row in gold.iterrows():
        res, av = parse_anotacion(row.get(col))
        for x in av:
            avisos.append(f"review_id {row.review_id}: {x}")
        if res is None:
            continue
        if any(x.startswith("token inválido") for x in av):
            excluidos.append(int(row.review_id))   # ambiguo: no se cuenta como «sin aspecto»
            continue
        G[int(row.review_id)] = res
    return gold, G, avisos, excluidos


def _registrar_uso_test(a, version, conjunto):
    log = Path(a.log_test)
    previos = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    if any(f"\t{version}\t" in l for l in previos):
        print(f"\n*** AVISO (M3.1): el conjunto de prueba ya se usó con la versión '{version}'. "
              f"Reporta el PRIMER resultado; repetir hasta que salga bien invalida la medición. ***\n")
    elif previos:
        print(f"\nAviso: el conjunto de prueba ya se usó {len(previos)} vez/veces con otras versiones (queda registro en {log}).\n")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{version}\t{conjunto}\t{_sha(a.pred)}\t{_sha(a.gold)}\n")


def cmd_evaluar(a):
    if a.conjunto in ("test", "todos") and not a.confirmar_test:
        sys.exit("El conjunto de prueba se usa UNA sola vez por versión candidata (M3.1).\n"
                 "Si la versión ya está congelada, repite el comando con --confirmar-test.")
    gold, G, avisos, excluidos = _cargar_gold(a.gold)
    if a.conjunto != "todos":
        permitidos = set(gold[gold.conjunto == a.conjunto].review_id.astype(int))
        G = {k: v for k, v in G.items() if k in permitidos}
    for x in avisos:
        print("AVISO:", x)
    if excluidos:
        print(f"AVISO: {len(excluidos)} comentarios con tokens inválidos quedan fuera de la evaluación: {excluidos[:10]}")
    if not G:
        sys.exit("No hay comentarios anotados en ese conjunto.")
    P, version = _cargar_pred(a.pred, a.version)
    if a.conjunto in ("test", "todos"):
        _registrar_uso_test(a, version, a.conjunto)
    P = {k: v for k, v in P.items() if k in G}
    cnt = _conteos(G, P)
    f1_pol, f1_det = _micro(cnt)
    ic_pol, ic_det = _bootstrap(cnt)
    tp_pol, tp_det, n_pred, n_gold = cnt.sum(0)
    print(f"Versión evaluada: {version} | conjunto: {a.conjunto} | {len(G)} comentarios anotados "
          f"| aspectos en gold: {int(n_gold)} | en predicción: {int(n_pred)}\n")
    print(f"{'aspecto':28s} {'prec':>6s} {'recall':>7s} {'F1':>6s} {'F1 det':>7s} {'pol.ok':>7s} {'n_gold':>7s} {'n_pred':>7s}")
    por_aspecto, f1s_pol, f1s_det = {}, [], []
    for c, nombre in CODIGOS.items():
        g = {(r, c): s for r, d in G.items() for cc, s in d.items() if cc == c}
        p = {(r, c): s for r, d in P.items() for cc, s in d.items() if cc == c}
        t_det = len(set(g) & set(p))
        t_pol = sum(1 for k in g if p.get(k) == g[k])
        pr = t_pol / len(p) if p else 0.0
        rc = t_pol / len(g) if g else 0.0
        f_pol, f_det = _f1(t_pol, len(p), len(g)), _f1(t_det, len(p), len(g))
        acc = t_pol / t_det if t_det else 0.0
        print(f"{nombre:28s} {pr:6.2f} {rc:7.2f} {(f_pol or 0):6.2f} {(f_det or 0):7.2f} {acc:7.2f} {len(g):7d} {len(p):7d}")
        por_aspecto[nombre] = dict(**_precision_por_signo(G, P, c), f1_pol=f_pol, f1_det=f_det, precision_pol=pr, recall_pol=rc,
                                   exactitud_polaridad=acc, n_gold=len(g), n_pred=len(p))
        if g:
            f1s_pol.append(f_pol or 0.0)
            f1s_det.append(f_det or 0.0)
    # polaridad negativa (M3.6): las oportunidades que el coordinador no debe pasar por alto
    gn = {(r, c) for r, d in G.items() for c, s in d.items() if s == "-"}
    pn = {(r, c) for r, d in P.items() for c, s in d.items() if s == "-"}
    rec_neg = len(gn & pn) / len(gn) if gn else None
    pre_neg = len(gn & pn) / len(pn) if pn else None
    exact = tp_pol / tp_det if tp_det else 0.0
    macro_pol, macro_det = float(np.mean(f1s_pol)), float(np.mean(f1s_det))
    print(f"\nF1 macro (aspecto + polaridad):      {macro_pol:.3f}     F1 macro (detección): {macro_det:.3f}")
    print(f"F1 micro (detección):                {f1_det:.3f}   IC95% [{ic_det[0]:.3f}, {ic_det[1]:.3f}]")
    print(f"F1 micro (aspecto + polaridad):      {f1_pol:.3f}   IC95% [{ic_pol[0]:.3f}, {ic_pol[1]:.3f}]   <- el que compara con la meta de {META_F1}")
    print(f"Exactitud de polaridad (aspectos bien detectados): {exact:.3f}")
    if rec_neg is not None:
        print(f"Polaridad negativa: recall {rec_neg:.3f} ({len(gn & pn)}/{len(gn)})"
              + (f" | precisión {pre_neg:.3f}" if pre_neg is not None else ""))
    print(f"(IC por bootstrap de comentarios: {N_BOOTSTRAP} repeticiones, semilla {SEMILLA_BOOTSTRAP}.)")
    if a.json:
        res = dict(version_modelo=version, conjunto=a.conjunto, fecha=datetime.now().isoformat(timespec="seconds"),
                   n_comentarios=len(G), n_gold_aspectos=int(n_gold), n_pred_aspectos=int(n_pred),
                   f1_micro_pol=f1_pol, f1_micro_pol_ic95=ic_pol, f1_micro_det=f1_det, f1_micro_det_ic95=ic_det,
                   f1_macro_pol=macro_pol, f1_macro_det=macro_det, exactitud_polaridad=exact,
                   recall_negativos=rec_neg, precision_negativos=pre_neg, por_aspecto=por_aspecto,
                   gold_sha256=_sha(a.gold), pred_sha256=_sha(a.pred), bootstrap=N_BOOTSTRAP, semilla_bootstrap=SEMILLA_BOOTSTRAP)
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Métricas guardadas en {a.json}")
    return 0


# ---------------------------------------------------------------- kappa
def _kappa(a_lista, b_lista, clases):
    ix = {c: i for i, c in enumerate(clases)}
    m = np.zeros((len(clases), len(clases)))
    for x, y in zip(a_lista, b_lista):
        m[ix[x], ix[y]] += 1
    n = m.sum()
    po = np.trace(m) / n
    pe = (m.sum(1) * m.sum(0)).sum() / n ** 2
    return None if pe == 1 else (po - pe) / (1 - pe), po, m


def cmd_kappa(a):
    _, GA, avA, _x = _cargar_gold(a.a, "anotacion")
    _, GB, avB, _y = _cargar_gold(a.b, a.col_b)
    for x in avA + avB:
        print("AVISO:", x)
    comunes = sorted(set(GA) & set(GB))
    if not comunes:
        sys.exit("No hay comentarios anotados por ambas personas.")
    ca, cb = [], []
    for rid in comunes:
        for c in CODIGOS:
            ca.append(GA[rid].get(c, "_"))
            cb.append(GB[rid].get(c, "_"))
    k, po, _m = _kappa(ca, cb, ["_", "+", "-", "0"])
    cnt = _conteos({r: GA[r] for r in comunes}, {r: GB[r] for r in comunes})
    f1_pol, f1_det = _micro(cnt)
    ambos = [(x, y) for x, y in zip(ca, cb) if x != "_" and y != "_"]
    print(f"{len(comunes)} comentarios anotados por ambas personas ({len(ca)} celdas comentario × aspecto)")
    print(f"Kappa de Cohen (4 clases: sin aspecto, +, -, 0): {k:.3f}   acuerdo observado {po:.3f}")
    if ambos:
        print(f"Cuando ambos marcan el aspecto, coinciden en el signo en {sum(1 for x, y in ambos if x == y) / len(ambos):.1%} ({len(ambos)} casos)")
    print(f"F1 de acuerdo (A como referencia): aspecto+polaridad {f1_pol:.3f} | solo detección {f1_det:.3f}")
    print("Lectura: es una cota realista de lo que un modelo puede alcanzar con esta guía de anotación.")
    return 0


# ---------------------------------------------------------------- identidad (M3.4)
SONDAS = ["Fair", "Sweet", "Clear", "Good", "Best", "Nice", "Kind", "Great", "Hard", "Easy", "Tough", "Terrible"]


def _preds(texto, mascara):
    return {(x, y) for x, y, _e in etiquetar_texto(texto, _signo_lexico, None, mascara)}


def cmd_identidad(a):
    """M3.4. Dos pruebas, ambas elegidas SIN usar la máscara (si estuviera rota, la prueba fallaría):
    A) el nombre literal del profesor se cambia por el de otro profesor y las predicciones no cambian;
    B) el apellido tras un título («Dr. X», «Professor X») se cambia por palabras con carga («Fair», «Sweet»...)
       y las predicciones no cambian."""
    rev = _comentarios_reales(a.review)
    prof = pd.read_csv(a.profesor, usecols=["profesor_id", "nombre"]).set_index("profesor_id").nombre
    masc = _mascaras(a.profesor)
    toks = {pid: tokens_nombre(n) for pid, n in prof.items()}
    libres = [pid for pid in prof.index if toks[pid] and not any(_palabra_cargada(t) for t in toks[pid])]
    libres_set = set(libres)
    rng = np.random.default_rng(a.semilla)
    ocurre = lambda tk, t: re.search(r"\b" + re.escape(tk) + r"\b", t, re.I)
    filas = list(zip(rev.review_id, rev.profesor_id, rev.comentario))
    print(f"{len(filas):,} comentarios con texto real; {len(prof) - len(libres)} profesores con algún token "
          f"con carga en el nombre (solo la prueba B los incluye).")
    fallos = {"A": [], "B": []}
    totales = {}

    # A) nombre literal -> nombre de otro profesor (sin tokens con carga en ninguno de los dos)
    elegibles = [f for f in filas if f[1] in libres_set and any(ocurre(tk, f[2]) for tk in toks[f[1]])]
    muestra = [elegibles[i] for i in rng.choice(len(elegibles), min(a.n, len(elegibles)), replace=False)]
    totales["A"] = len(muestra)
    for rid, pid, t in muestra:
        otro = int(rng.choice([p for p in libres if p != pid]))
        t2 = t
        for i, tk in enumerate(toks[pid]):
            t2 = re.sub(r"\b" + re.escape(tk) + r"\b", toks[otro][i % len(toks[otro])], t2, flags=re.I)
        d = _preds(t, masc[pid]) ^ _preds(t2, masc[otro])
        if d:
            fallos["A"].append((rid, d))

    # B) apellido tras título -> palabra con carga (no se incluyen posesivos: limitación conocida, ver crear_mascara)
    elegibles = [f for f in filas if re.search(TITULO_NOMBRE.pattern + r"(?!['’])", f[2])]
    muestra = [elegibles[i] for i in rng.choice(len(elegibles), min(a.n, len(elegibles)), replace=False)]
    totales["B"] = len(muestra)
    for k, (rid, pid, t) in enumerate(muestra):
        sonda = SONDAS[k % len(SONDAS)]
        t2 = re.sub(r"(" + TITULO_NOMBRE.pattern.rsplit(r"\s*", 1)[0] + r")\s*[A-Z][A-Za-z\-]+(?!['’])",
                    lambda m: m.group(1) + " " + sonda, t)
        d = _preds(t, masc[pid]) ^ _preds(t2, masc[pid])
        if d:
            fallos["B"].append((rid, d))

    print()
    for k, etiqueta in (("A", "nombre literal -> otro profesor"), ("B", "título + apellido -> palabra con carga")):
        ok = totales[k] - len(fallos[k])
        print(f"Prueba {k} ({etiqueta}): {ok} de {totales[k]} idénticas -> {'PASA' if not fallos[k] else 'FALLA'}")
        for rid, d in fallos[k][:5]:
            print(f"    review_id {rid}: difieren {sorted(d)}")
    todo = not fallos["A"] and not fallos["B"]
    print(f"\nPrueba de identidad M3.4: {'PASA' if todo else 'FALLA'}")
    return 0 if todo else 1


# ---------------------------------------------------------------- re-anotar el signo de un aspecto (regla de Rigor)
def _leer_csv(ruta):
    with Path(ruta).open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        return lector.fieldnames, list(lector)


def _escribir_csv(ruta, campos, filas):
    """Mismo formato que anotar_gold.py (BOM, saltos \\n); escritura atómica."""
    ruta = Path(ruta)
    tmp = ruta.with_name(ruta.name + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)
    tmp.replace(ruta)


def cmd_preparar_aspecto(a):
    """Archivo de trabajo con los comentarios que tienen el aspecto en el gold, SIN su signo actual (a ciegas)."""
    cod = a.aspecto.upper()
    col = f"anotacion_{cod.lower()}"
    salida = Path(a.salida or f"data/gold_{cod.lower()}_resign.csv")
    if salida.exists() and not a.forzar:
        sys.exit(f"{salida} ya existe; no se sobrescribe (podría tener re-anotaciones). Usa --forzar solo si empiezas de cero.")
    _, filas = _leer_csv(a.gold)
    elegidas = []
    for f in filas:
        res, _av = parse_anotacion(f["anotacion"])
        if res is None:
            sys.exit(f"review_id {f['review_id']} no está anotado en {a.gold}: termina el gold antes.")
        if cod in res:
            elegidas.append({"review_id": f["review_id"], "comentario": f["comentario"], col: ""})
    salida.parent.mkdir(parents=True, exist_ok=True)
    _escribir_csv(salida, ["review_id", "comentario", col], elegidas)
    print(f"{len(elegidas)} de {len(filas)} comentarios tienen {cod} -> {salida} (columna '{col}' vacía; sin el signo anterior).")
    print(f"Re-anota con: python anotar_gold.py --gold {salida} --columna {col} --solo {cod}")
    return 0


def cmd_fusionar_aspecto(a):
    """Devuelve al gold SOLO el signo re-anotado de un aspecto; el resto de cada anotación queda intacto."""
    cod = a.aspecto.upper()
    col = a.columna or f"anotacion_{cod.lower()}"
    _, trabajo = _leer_csv(a.parcial)
    nuevos, pendientes = {}, []
    for f in trabajo:
        v = (f.get(col) or "").strip()
        if v == "":
            pendientes.append(f["review_id"])
        elif v == "ninguno":                       # «no es este aspecto»: se quita del comentario
            nuevos[f["review_id"]] = None
        else:
            m = re.fullmatch(cod + r"([+\-0])", v)
            if not m:
                sys.exit(f"review_id {f['review_id']}: valor '{v}' inválido (se espera {cod}+, {cod}0, {cod}- o 'ninguno').")
            nuevos[f["review_id"]] = m.group(1)
    if pendientes:
        sys.exit(f"Faltan {len(pendientes)} de {len(trabajo)} comentarios por re-anotar en {a.parcial}; no se fusiona nada.")
    campos, filas = _leer_csv(a.gold)
    faltan = set(nuevos) - {f["review_id"] for f in filas}
    if faltan:
        sys.exit(f"{len(faltan)} review_id del archivo de trabajo no están en {a.gold}: {sorted(faltan)[:5]}")
    respaldo = Path(a.gold).with_name(Path(a.gold).stem + f".antes_{cod.lower()}.csv")
    if not respaldo.exists():
        shutil.copy2(a.gold, respaldo)
    cambios = collections.Counter()
    for f in filas:
        rid = f["review_id"]
        if rid not in nuevos:
            continue
        nuevo = nuevos[rid]
        toks = f["anotacion"].split()
        viejo = next((t[3] for t in toks if t[:3].upper() == cod), None)
        salida = []
        for t in toks:
            if t[:3].upper() != cod:
                salida.append(t)
            elif nuevo is not None:
                salida.append(cod + nuevo)
        if viejo is None and nuevo is not None:
            salida.append(cod + nuevo)
        salida = [t for t in salida if t != "ninguno"]
        f["anotacion"] = " ".join(salida) if salida else "ninguno"
        cambios[(viejo or "—", nuevo or "quitado")] += 1
    _escribir_csv(a.gold, campos, filas)
    print(f"{len(nuevos)} comentarios actualizados en {a.gold} (respaldo previo: {respaldo}). Solo cambió {cod}.")
    print("Signo anterior -> nuevo:")
    for (v, n), k in sorted(cambios.items(), key=lambda kv: -kv[1]):
        print(f"  {cod}{v if v != '—' else ' (no estaba)'} -> {cod + n if n != 'quitado' else 'quitado'}: {k}")
    return 0


# ---------------------------------------------------------------- registrar
def cmd_registrar(a):
    m = json.loads(Path(a.metricas).read_text(encoding="utf-8"))
    f1 = m["f1_micro_pol"]
    validado = m["conjunto"] == "test" and f1 is not None and f1 >= META_F1
    estado = "validado" if validado else "en_calibracion"
    if a.pred and any("prec_pos" not in v for v in m["por_aspecto"].values()):
        # Métricas de una evaluación anterior a la compuerta C: se completan con las MISMAS predicciones y el mismo
        # conjunto (no es una evaluación nueva; no se registra en uso_test.log).
        gold, G, _, _ = _cargar_gold(a.gold)
        if m["conjunto"] != "todos":
            ids = set(gold[gold.conjunto == m["conjunto"]].review_id.astype(int))
            G = {k: v for k, v in G.items() if k in ids}
        P, version = _cargar_pred(a.pred)
        if version != m["version_modelo"]:
            sys.exit(f"--pred es de '{version}' y las métricas de '{m['version_modelo']}'.")
        for cod, nombre in CODIGOS.items():
            m["por_aspecto"][nombre].update(_precision_por_signo(G, {k: v for k, v in P.items() if k in G}, cod))
        print("Precisión por signo completada a partir de --pred (mismas predicciones y conjunto que las métricas).")
    campos = ("f1_pol", "f1_det", "n_gold", "prec_pos", "n_pred_pos", "prec_neg", "n_pred_neg")
    por_aspecto = {k: {c: v[c] for c in campos if c in v} for k, v in m["por_aspecto"].items()}
    fila = dict(version_modelo=m["version_modelo"], fecha=datetime.now().isoformat(timespec="seconds"),
                descripcion=a.descripcion, estado=estado, f1_micro=round(f1, 4),
                f1_por_aspecto=json.dumps(por_aspecto, ensure_ascii=False), n_gold=m["n_comentarios"])
    ruta = Path(a.salida)
    df = pd.read_csv(ruta) if ruta.exists() else pd.DataFrame(columns=list(fila))
    df = pd.concat([df[df.version_modelo != fila["version_modelo"]], pd.DataFrame([fila])], ignore_index=True)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8")
    if m["conjunto"] != "test":
        print(f"Métricas de '{m['conjunto']}': el estado queda en_calibracion (solo el TEST puede validar el modelo).")
    elif not validado:
        print(f"F1 en test = {f1:.3f} < {META_F1}: estado en_calibracion (la página mostrará la insignia con el valor).")
    else:
        print(f"F1 en test = {f1:.3f} >= {META_F1}: estado validado.")
    q = lambda s: str(s).replace("'", "''")
    print(f"Fila escrita en {ruta}. SQL para Supabase:\n")
    print("insert into modelo_version (version_modelo, descripcion, estado, f1_micro, f1_por_aspecto, n_gold)\n"
          f"values ('{q(fila['version_modelo'])}', '{q(a.descripcion)}', '{estado}', {fila['f1_micro']}, "
          f"'{q(fila['f1_por_aspecto'])}'::jsonb, {fila['n_gold']})\n"
          "on conflict (version_modelo) do update set descripcion = excluded.descripcion, estado = excluded.estado,\n"
          "  f1_micro = excluded.f1_micro, f1_por_aspecto = excluded.f1_por_aspecto, n_gold = excluded.n_gold, fecha = now();")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    REV, PROF, PART = "data/review.csv", "data/profesor.csv", "data/particion_profesor.csv"
    GOLD, GOLD2, PRED = "data/gold_para_anotar.csv", "data/gold_doble_para_anotar.csv", "data/review_aspecto.csv"

    p = sub.add_parser("particion"); p.add_argument("--profesor", default=PROF); p.add_argument("--review", default=REV)
    p.add_argument("--salida", default=PART); p.add_argument("--frac", type=float, default=0.15)
    p.add_argument("--semilla", type=int, default=SEMILLA_PARTICION); p.add_argument("--forzar", action="store_true")

    p = sub.add_parser("muestra"); p.add_argument("--review", default=REV); p.add_argument("--particion", default=PART)
    p.add_argument("--n", type=int, default=399); p.add_argument("--dev-por-estrato", type=int, default=33)
    p.add_argument("--n-doble", type=int, default=50); p.add_argument("--salida", default=GOLD)
    p.add_argument("--salida-doble", default=GOLD2); p.add_argument("--forzar", action="store_true")

    p = sub.add_parser("etiquetar"); p.add_argument("--review", default=REV); p.add_argument("--profesor", default=PROF)
    p.add_argument("--salida", default=PRED); p.add_argument("--polaridad", choices=["lexico", "hf"], default="lexico")
    p.add_argument("--reglas", choices=["v0.2", "v0.3"], default="v0.2", help="v0.3 = reglas de signo del criterio denso (D7-D9) para RIG/CAR/ASI")

    p = sub.add_parser("evaluar"); p.add_argument("--gold", default=GOLD); p.add_argument("--pred", default=PRED)
    p.add_argument("--conjunto", choices=["dev", "test", "todos"], default="dev"); p.add_argument("--version")
    p.add_argument("--confirmar-test", action="store_true"); p.add_argument("--json")
    p.add_argument("--log-test", default="data/uso_test.log")

    p = sub.add_parser("identidad"); p.add_argument("--review", default=REV); p.add_argument("--profesor", default=PROF)
    p.add_argument("--n", type=int, default=500); p.add_argument("--semilla", type=int, default=42)

    p = sub.add_parser("kappa"); p.add_argument("--a", default=GOLD); p.add_argument("--b", default=GOLD2)
    p.add_argument("--col-b", default="anotacion_2")

    p = sub.add_parser("preparar-aspecto"); p.add_argument("--gold", default=GOLD); p.add_argument("--aspecto", default="RIG")
    p.add_argument("--salida"); p.add_argument("--forzar", action="store_true")

    p = sub.add_parser("fusionar-aspecto"); p.add_argument("--gold", default=GOLD); p.add_argument("--aspecto", default="RIG")
    p.add_argument("--parcial", default="data/gold_rig_resign.csv"); p.add_argument("--columna")

    p = sub.add_parser("registrar"); p.add_argument("--metricas", required=True)
    p.add_argument("--descripcion", required=True); p.add_argument("--salida", default="data/modelo_version.csv")
    p.add_argument("--pred", help="predicciones evaluadas, para completar la precisión por signo si las métricas no la traen")
    p.add_argument("--gold", default=GOLD)

    args = ap.parse_args()
    sys.exit({"particion": cmd_particion, "muestra": cmd_muestra, "etiquetar": cmd_etiquetar, "evaluar": cmd_evaluar,
              "identidad": cmd_identidad, "kappa": cmd_kappa, "registrar": cmd_registrar,
              "preparar-aspecto": cmd_preparar_aspecto, "fusionar-aspecto": cmd_fusionar_aspecto}[args.cmd](args))
