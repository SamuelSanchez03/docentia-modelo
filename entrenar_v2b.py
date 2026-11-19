#!/usr/bin/env python3
"""
entrenar_v2b.py - v2b: ajuste fino de distilroberta-base por oración (9 cabezas × 4 clases) con el silver.

  python entrenar_v2b.py entrenar                    # en CPU; guarda al final de cada época y se reanuda con el mismo comando
  python entrenar_v2b.py calibrar                    # F1 en dev para varios umbrales; fija UN umbral global (M2.5)
  python entrenar_v2b.py predecir --conjunto dev     # -> data/modelos/v2b/review_aspecto_v2b_dev.csv (para `absa_baseline.py evaluar`)
  python entrenar_v2b.py predecir --conjunto todos   # -> data/review_aspecto_<versión>.csv (solo para la elegida)

  Otro modelo base (cada uno en su carpeta; calibrar/predecir leen el base de config.json):
  python entrenar_v2b.py entrenar --base roberta-base --dir data/modelos/v2b_roberta
  python entrenar_v2b.py calibrar --dir data/modelos/v2b_roberta

Mismo preprocesamiento que v0, el silver y v2a (absa_baseline.frases + crear_mascara); misma validación interna que v2a
(10 % de los profesores del silver, semilla 42). Hiperparámetros fijados de antemano: lr 2e-5, lote 32, 3 épocas, 96 tokens,
pérdida ponderada por clase. La mejor época se elige en la validación interna del silver, nunca en dev.
"""
import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

import absa_baseline as A
from entrenar_v2a import COD, SEMILLA, _consolidar, _f1_comentarios, _silver

BASE = "distilroberta-base"
VERSION = "v2b-distilroberta"
UMBRALES = np.unique(np.round(np.concatenate([np.arange(0.30, 0.90, 0.05), np.arange(0.90, 0.995, 0.01)]), 2))


class ABSA(nn.Module):
    def __init__(self, base=BASE):
        super().__init__()
        self.enc = AutoModel.from_pretrained(base)
        self.drop = nn.Dropout(0.1)
        self.head = nn.Linear(self.enc.config.hidden_size, len(COD) * 4)

    def forward(self, input_ids, attention_mask):
        h = self.enc(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0]
        return self.head(self.drop(h)).view(-1, len(COD), 4)


def _lotes(n, tam, rng=None):
    idx = rng.permutation(n) if rng is not None else np.arange(n)
    for i in range(0, n, tam):
        yield idx[i:i + tam]


def _tok(tok, textos, maxlen):
    return tok(list(textos), truncation=True, max_length=maxlen, padding=True, return_tensors="pt")


@torch.no_grad()
def _probs(model, tok, textos, maxlen, tam=64, avisar=False):
    """dict aspecto -> matriz (n, 4) de probabilidades (columna 0 = no_menciona)."""
    model.eval()
    out, t0 = [], time.time()
    for k, b in enumerate(_lotes(len(textos), tam), 1):
        e = _tok(tok, [textos[i] for i in b], maxlen)
        out.append(torch.softmax(model(e["input_ids"], e["attention_mask"]), -1).numpy())
        if avisar and k % 50 == 0:
            print(f"  {k * tam:,}/{len(textos):,} oraciones · {(time.time() - t0) / 60:.1f} min", flush=True)
    P = np.concatenate(out) if out else np.zeros((0, len(COD), 4))
    return {c: P[:, j, :] for j, c in enumerate(COD)}


def _particion(s):
    """Misma validación interna que v2a: 10 % de los profesores del silver, semilla 42."""
    profs = np.array(sorted(s.profesor_id.unique()))
    val = set(np.random.default_rng(SEMILLA).choice(profs, int(round(0.10 * len(profs))), replace=False))
    es_val = s.profesor_id.isin(val).values
    return s[~es_val].reset_index(drop=True), s[es_val].reset_index(drop=True)


def cmd_entrenar(a):
    out = Path(a.dir)
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(SEMILLA)
    np.random.seed(SEMILLA)
    if a.hilos:
        torch.set_num_threads(a.hilos)
    s, gold = _silver()
    tr, va = _particion(s)
    if a.max_oraciones:                                   # solo para pruebas rápidas
        tr, va = tr.iloc[:a.max_oraciones], va.iloc[:max(40, a.max_oraciones // 4)]
    Y = torch.tensor(tr[COD].values, dtype=torch.long)
    pesos = []                                            # raíz del inverso de la frecuencia, por aspecto
    for c in COD:
        n = np.bincount(tr[c].values, minlength=4) + 1
        w = np.sqrt(n.sum() / (4 * n))
        pesos.append(torch.tensor(w / w.mean(), dtype=torch.float))
    ce = [nn.CrossEntropyLoss(weight=w) for w in pesos]
    tok = AutoTokenizer.from_pretrained(a.base)
    model = ABSA(a.base)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    pasos = math.ceil(len(tr) / a.lote)
    sch = get_linear_schedule_with_warmup(opt, int(0.1 * pasos * a.epocas), pasos * a.epocas)
    ck, ep0, mejor = out / "checkpoint.pt", 0, None
    if ck.exists() and not a.desde_cero:
        st = torch.load(ck, weights_only=False)
        model.load_state_dict(st["modelo"]); opt.load_state_dict(st["opt"]); sch.load_state_dict(st["sch"])
        ep0, mejor = st["epoca"], st["mejor"]
        print(f"Reanudando después de la época {ep0} (mejor hasta ahora: {mejor})", flush=True)
    print(f"Entrenamiento: {len(tr):,} oraciones · validación interna: {len(va):,} · {pasos} pasos por época · "
          f"{a.epocas} épocas · {torch.get_num_threads()} hilos", flush=True)
    textos = tr.oracion.tolist()
    for ep in range(ep0, a.epocas):
        model.train()
        t0, acum = time.time(), 0.0
        for k, b in enumerate(_lotes(len(tr), a.lote, np.random.default_rng(SEMILLA + ep)), 1):
            e = _tok(tok, [textos[i] for i in b], a.maxlen)
            logits = model(e["input_ids"], e["attention_mask"])
            y = Y[b]
            loss = sum(ce[j](logits[:, j, :], y[:, j]) for j in range(len(COD)))
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sch.step()
            acum += loss.item()
            if k % a.cada == 0 or k == pasos:
                el = time.time() - t0
                print(f"  época {ep + 1}/{a.epocas} · paso {k}/{pasos} · pérdida {acum / k:.3f} · {el / 60:.1f} min · "
                      f"faltan ~{el / k * (pasos - k) / 60:.0f} min de esta época", flush=True)
        print(f"Época {ep + 1}: evaluando en la validación interna...", flush=True)
        P = _probs(model, tok, va.oracion.tolist(), a.maxlen)
        ids = va.review_id.tolist()
        fp, fd, t = max((*_f1_comentarios(_consolidar(ids, P, t), gold, sorted(set(ids))), float(t)) for t in UMBRALES)
        print(f"Época {ep + 1}: validación interna (contra el silver) · F1 aspecto+pol {fp:.3f} · detección {fd:.3f} · t={t}", flush=True)
        if mejor is None or fp > mejor["f1_pol"]:
            mejor = dict(epoca=ep + 1, f1_pol=round(fp, 4), f1_det=round(fd, 4), t=t)
            torch.save(model.state_dict(), out / "modelo.pt")
        torch.save(dict(modelo=model.state_dict(), opt=opt.state_dict(), sch=sch.state_dict(), epoca=ep + 1, mejor=mejor), ck)
    tok.save_pretrained(out / "tokenizer")
    version = VERSION if a.base == BASE else "v2b-" + a.base.split("/")[-1]
    cfg = dict(version=version, base=a.base, maxlen=a.maxlen, lote=a.lote, lr=a.lr, epocas=a.epocas, semilla=SEMILLA,
               t=mejor["t"], mejor_epoca=mejor["epoca"], val_f1_pol=mejor["f1_pol"], val_f1_det=mejor["f1_det"],
               n_oraciones_train=len(tr), n_oraciones_val=len(va), silver_prompt=sorted(s.prompt.unique()),
               torch=torch.__version__, fecha=datetime.now().isoformat(timespec="seconds"))
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo. Mejor época {mejor['epoca']} (umbral {mejor['t']}) guardada en {out / 'modelo.pt'}. "
          f"Puedes borrar {ck} (~1 GB) si no vas a reanudar.", flush=True)
    return 0


def _cargar(d):
    cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
    tok = AutoTokenizer.from_pretrained(d / "tokenizer")
    model = ABSA(cfg.get("base", BASE))
    model.load_state_dict(torch.load(d / "modelo.pt", weights_only=True))
    return model, tok, cfg


def _oraciones(conjunto):
    import pandas as pd
    rev = A._comentarios_reales("data/review.csv")
    if conjunto in ("dev", "test"):
        g = pd.read_csv("data/gold_para_anotar.csv", encoding="utf-8-sig")
        rev = rev[rev.review_id.isin(g[g.conjunto == conjunto].review_id)]
    masc = A._mascaras("data/profesor.csv")
    ids, orig, enm = [], [], []
    for rid, pid, texto in zip(rev.review_id, rev.profesor_id, rev.comentario):
        for i, f in A.frases(texto):
            o = texto[i:f].strip()
            ids.append(int(rid)); orig.append(o); enm.append(masc[pid](o))
    return ids, orig, enm


def cmd_calibrar(a):
    """Un solo umbral global en dev (M2.5). Cuenta como UNA evaluación de v2b en dev."""
    d = Path(a.dir)
    model, tok, cfg = _cargar(d)
    ids, _, enm = _oraciones("dev")
    P = _probs(model, tok, enm, cfg["maxlen"])
    _, G, _, _ = A._cargar_gold("data/gold_para_anotar.csv", "anotacion")
    dev = set(ids)
    G = {k: v for k, v in G.items() if k in dev}
    filas = []
    for t in UMBRALES:
        pred = {rid: {c: s for c, (s, _) in asp.items()} for rid, asp in _consolidar(ids, P, t).items()}
        fp, fd = A._micro(A._conteos(G, pred))
        filas.append((fp, fd, float(t), sum(len(v) for v in pred.values())))
    print(f"{'umbral':>7} {'F1 asp+pol':>11} {'F1 det':>7} {'n_pred':>7}   (gold: {sum(len(v) for v in G.values())} aspectos)")
    for fp, fd, t, n in filas:
        print(f"{t:7.2f} {fp:11.3f} {fd:7.3f} {n:7d}" + ("   <- silver" if t == cfg["t"] else ""))
    fp, fd, t, _ = max(filas)
    cfg["t_dev"] = t
    (d / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nUmbral fijado con dev: t={t} (F1 aspecto+pol {fp:.3f}, detección {fd:.3f}); umbral del silver: {cfg['t']}.")
    print("Ojo: el F1 de dev con un umbral elegido en dev es optimista; la cifra que cuenta es la de test.")
    return 0


def cmd_predecir(a):
    import pandas as pd
    d = Path(a.dir)
    model, tok, cfg = _cargar(d)
    t = a.umbral if a.umbral is not None else cfg.get("t_dev", cfg["t"])
    ids, orig, enm = _oraciones(a.conjunto)
    print(f"{len(set(ids)):,} comentarios -> {len(ids):,} oraciones; umbral t={t}", flush=True)
    final = _consolidar(ids, _probs(model, tok, enm, cfg["maxlen"], avisar=True), t)
    filas = []
    for rid, asp in final.items():
        for c in COD:
            if c in asp:
                sig, k = asp[c]
                ev = orig[k][:280].rsplit(" ", 1)[0] if len(orig[k]) > 280 else orig[k]
                filas.append((rid, A.CODIGOS[c], A.POL[sig], ev, cfg["version"]))
    outp = pd.DataFrame(filas, columns=["review_id", "aspecto", "polaridad", "evidencia", "version_modelo"])
    outp.insert(0, "review_aspecto_id", range(1, len(outp) + 1))
    ruta = d / f"review_aspecto_v2b_{a.conjunto}.csv" if a.conjunto in ("dev", "test") else Path(f"data/review_aspecto_{cfg['version'].replace('-', '_')}.csv")
    outp.to_csv(ruta, index=False, encoding="utf-8")
    print(f"{len(outp):,} filas en {ruta}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("entrenar")
    p.add_argument("--epocas", type=int, default=3); p.add_argument("--lote", type=int, default=32)
    p.add_argument("--lr", type=float, default=2e-5); p.add_argument("--maxlen", type=int, default=96)
    p.add_argument("--hilos", type=int, default=0, help="hilos de CPU para torch (0 = valor por defecto)")
    p.add_argument("--cada", type=int, default=20, help="imprimir progreso cada N pasos")
    p.add_argument("--max-oraciones", type=int, default=0, help="solo para pruebas rápidas")
    p.add_argument("--desde-cero", action="store_true", help="ignorar el checkpoint y empezar de nuevo")
    p.add_argument("--dir", default="data/modelos/v2b")
    p.add_argument("--base", default=BASE, help="modelo base de Hugging Face (p. ej. roberta-base); usa otro --dir")
    p = sub.add_parser("calibrar"); p.add_argument("--dir", default="data/modelos/v2b")
    p = sub.add_parser("predecir"); p.add_argument("--conjunto", choices=["dev", "test", "todos"], default="dev")
    p.add_argument("--umbral", type=float); p.add_argument("--dir", default="data/modelos/v2b")
    a = ap.parse_args()
    sys.exit({"entrenar": cmd_entrenar, "calibrar": cmd_calibrar, "predecir": cmd_predecir}[a.cmd](a))
