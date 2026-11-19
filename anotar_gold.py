#!/usr/bin/env python3
"""
anotar_gold.py - Herramienta local para anotar el gold (un comentario a la vez, con atajos de teclado).

Uso (desde la carpeta del proyecto):
  python anotar_gold.py                                   # anota data/gold_para_anotar.csv (columna 'anotacion')
  python anotar_gold.py --gold data/gold_doble_para_anotar.csv --columna anotacion_2   # la segunda persona
  python anotar_gold.py --gold data/gold_rig_resign.csv --columna anotacion_rig --solo RIG   # solo el signo de Rigor

Se abre http://127.0.0.1:8765 en el navegador. Cada cambio se guarda al instante en el CSV (escritura atómica;
la primera vez se crea una copia <archivo>.bak con el original vacío). Para terminar: Ctrl+C en la terminal.

Qué ve quien anota: SOLO el texto del comentario. El servidor no envía estrellas, nombre del profesor, conjunto
(dev/test) ni predicciones del modelo: el CSV del gold no los contiene y esta herramienta no lee ningún otro archivo.

Cierra el CSV en Excel/LibreOffice mientras anotas: si lo guardas desde ahí, pisas lo que escribió esta herramienta.
Solo escucha en 127.0.0.1 y exige un token aleatorio por sesión.

Formato de la anotación (idéntico al que lee absa_baseline.py): "CAL+ RIG0 CLI+"; sin aspecto: "ninguno";
celda vacía = no anotado.
"""
import argparse
import csv
import json
import re
import secrets
import shutil
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CODIGOS = ["RET", "CLA", "CAL", "ACC", "CAR", "RIG", "ORG", "CLI", "ASI"]
TOKEN = re.compile(r"[A-Z]{3}[+\-0]")


def anotacion_valida(texto):
    """'' (borrar), 'ninguno' o tokens CODIGO+signo sin repetir aspecto."""
    if texto in ("", "ninguno"):
        return True
    tokens = texto.split(" ")
    if not all(TOKEN.fullmatch(t) and t[:3] in CODIGOS for t in tokens):
        return False
    return len({t[:3] for t in tokens}) == len(tokens)


class Gold:
    """CSV del gold en memoria; cada guardado reescribe el archivo completo de forma atómica."""

    def __init__(self, ruta, columna):
        self.ruta, self.columna, self.lock = Path(ruta), columna, threading.Lock()
        with self.ruta.open(encoding="utf-8-sig", newline="") as f:
            lector = csv.DictReader(f)
            self.campos = lector.fieldnames
            self.filas = list(lector)
        for req in ("review_id", "comentario", columna):
            if req not in self.campos:
                sys.exit(f"{ruta} no tiene la columna '{req}' (columnas: {self.campos}).")
        self.indice = {f["review_id"]: i for i, f in enumerate(self.filas)}
        bak = self.ruta.with_name(self.ruta.name + ".bak")
        if not bak.exists():
            shutil.copy2(self.ruta, bak)

    def items(self):
        return [{"id": f["review_id"], "texto": f["comentario"], "anot": f[self.columna] or ""} for f in self.filas]

    def escribir(self):
        tmp = self.ruta.with_name(self.ruta.name + ".tmp")
        with tmp.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.campos, lineterminator="\n")
            w.writeheader()
            w.writerows(self.filas)
        tmp.replace(self.ruta)

    def guardar(self, review_id, anotacion):
        with self.lock:
            i = self.indice[review_id]
            self.filas[i][self.columna] = anotacion
            self.escribir()

    def resumen(self):
        hechas = sum(1 for f in self.filas if (f[self.columna] or "").strip())
        return hechas, len(self.filas)


PAGINA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anotar gold</title>
<style>
:root{--ink:#222;--mut:#6b7280;--line:#e5e7eb;--bg:#f7f7f8;--card:#fff;--pos:#1f7a4d;--neg:#c2410c;--neu:#475569;--sel:#2563eb}
@media (prefers-color-scheme:dark){:root{--ink:#e8e8ea;--mut:#9ca3af;--line:#33363d;--bg:#15171b;--card:#1d2026;--pos:#4ade80;--neg:#fb923c;--neu:#94a3b8;--sel:#60a5fa}}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
.wrap{max-width:860px;margin:0 auto;padding:16px}
header{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;margin-bottom:12px}
.prog{flex:1;min-width:220px}.bar{height:8px;background:var(--line);border-radius:99px;overflow:hidden;margin-top:4px}
.bar>i{display:block;height:100%;background:var(--pos);width:0}
button{font:inherit;cursor:pointer;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 12px}
button:hover{border-color:var(--sel)}button.on{background:var(--sel);color:#fff;border-color:var(--sel)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:12px}
#texto{font-size:18px;line-height:1.6;white-space:pre-wrap;margin:0}
.meta{color:var(--mut);font-size:13px;margin-bottom:8px;display:flex;justify-content:space-between}
.fila{display:grid;grid-template-columns:28px 1fr auto;gap:10px;align-items:center;padding:7px 8px;border-radius:8px;border:1px solid transparent}
.fila.sel{border-color:var(--sel);background:color-mix(in srgb,var(--sel) 8%,transparent)}
.fila .k{color:var(--mut);font-weight:700;text-align:center}.fila .n b{display:inline-block;width:38px}.fila .h{color:var(--mut);font-size:12.5px}
.sg button{width:38px;padding:5px 0;font-weight:700}
.sg button.p.on{background:var(--pos);border-color:var(--pos)}.sg button.m.on{background:var(--neg);border-color:var(--neg)}.sg button.z.on{background:var(--neu);border-color:var(--neu)}
.acciones{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;margin-top:12px}
#estado{font-size:13px;color:var(--mut)}#estado.err{color:#dc2626;font-weight:700}
.actual{margin:10px 0 0;font-family:ui-monospace,monospace;font-size:14px;color:var(--mut)}
details{margin-top:8px}summary{cursor:pointer;color:var(--sel)}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}td,th{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
.fin{text-align:center;padding:30px;font-size:18px}
</style></head><body><div class="wrap">
<header>
 <div class="prog"><div id="prog">Cargando…</div><div class="bar"><i id="barra"></i></div></div>
 <div><button id="fTodos" class="on">Todos</button> <button id="fPend">Pendientes</button> <button id="sigPend" title="p">Siguiente pendiente (p)</button></div>
</header>
<div id="bannerSolo" class="card" style="display:none;padding:12px 16px;font-size:14px;border-color:var(--sel)"><b>Solo Rigor: el signo depende únicamente de lo que el texto dice sobre la EXIGENCIA o la forma de calificar.</b><br>Mencionada sin calificar («hard», «tough grader», «expects a lot», «easy A», «not hard») → <code>0</code> · calificada como justa/valiosa/llevadera («hard but fair», «worth it», «doable») → <code>+</code> · calificada como injusta/arbitraria/desmedida («unfair», «impossible», «grades on a whim») → <code>−</code> · juicios opuestos → <code>0</code>.<br><b>Prueba de aislamiento:</b> tapa todo lo que no hable de la exigencia; si el signo solo se sostiene por el resto del comentario (explica mal, gran clase, la recomienda), es <code>0</code>. Si «hard/easy» no habla de exigencia («hard to hear») → <b>No es Rigor (n)</b>.</div>
<div id="bannerDenso" class="card" style="padding:10px 14px;font-size:13.5px"><b>Criterio denso:</b> marca <b>todo</b> aspecto que el texto menciona, no solo el principal · elogio/crítica general al enseñante = <code>CAL±</code> · mención sin juicio = <code>0</code> · «take him / avoid» solo = nada.</div>
<div id="vista"></div>
<details class="card"><summary>Guía completa del criterio denso y atajos</summary>
<p><b>Se anota lo que el texto dice, no lo que implica ni la calificación del alumno.</b> + positivo · − negativo · 0 sin juicio o con juicios opuestos. Un aspecto una vez por comentario.</p>
<table>
<tr><td>Elogio/crítica general al enseñante («good teacher», «worst professor», «knowledgeable», «awesome class»)</td><td><code>CAL+</code> / <code>CAL-</code></td></tr>
<tr><td>Recomendar/rechazar sin razón («take him», «avoid at all cost»)</td><td>nada</td></tr>
<tr><td>«Hard» / «easy» / «tough» / «very difficult» sin más</td><td><code>RIG0</code></td></tr>
<tr><td>«Hard but fair / doable» · «unfair / impossible / ridiculous»</td><td><code>RIG+</code> · <code>RIG-</code></td></tr>
<tr><td><b>Signo de Rigor:</b> solo por lo que el texto dice de la exigencia, nunca por el tono del resto del comentario</td><td>prueba de aislamiento</td></tr>
<tr><td>«Lots of homework» · «only two pages» · «two papers» (cantidad sin adjetivo)</td><td><code>CAR-</code> · <code>CAR+</code> · <code>CAR0</code></td></tr>
<tr><td>Extra credit / bonus · «no attendance policy» · quiz sorpresa · quiz regular, asistencia obligatoria, participación, «online»</td><td><code>ASI+</code> · <code>ASI+</code> · <code>ASI-</code> · <code>ASI0</code></td></tr>
<tr><td>Persona amable/grosera, «cares», disponible, responde correos</td><td><code>ACC±</code></td></tr>
<tr><td>Humor, entusiasmo, inspiración, ambiente hostil</td><td><code>CLI±</code></td></tr>
<tr><td>Devuelve trabajos con comentarios / feedback</td><td><code>RET±</code></td></tr>
<tr><td>Exámenes vs lo enseñado, rúbrica, guías de estudio</td><td><code>CLA±</code></td></tr>
<tr><td>Estructura, orden, plazos, proyectos de equipo</td><td><code>ORG±</code></td></tr>
<tr><td>Solo contexto («I took PSYCH 337»), o ningún aspecto</td><td>nada / <code>ninguno</code></td></tr>
<tr><td>Sarcasmo: el sentido real; con duda razonable</td><td><code>0</code></td></tr>
</table>
<p><b>Teclado:</b> <code>1</code>–<code>9</code> elige aspecto · <code>+</code> <code>-</code> <code>0</code> pone el signo (repetirlo lo quita) · <code>n</code> sin aspectos · <code>c</code> borra todo · <code>→</code>/<code>Enter</code> siguiente · <code>←</code> anterior · <code>p</code> siguiente pendiente.</p>
</details></div>
<script>
const TOKEN="__TOKEN__", COLUMNA="__COLUMNA__", SOLO="__SOLO__";
let ASP=[["RET","Retroalimentación","trabajos devueltos y tiempos de respuesta"],["CLA","Claridad de evaluación","criterios, rúbricas, qué evalúan los exámenes"],
["CAL","Calidad de clase","cómo enseña: explicaciones, clases, material"],["ACC","Accesibilidad y trato","disponibilidad, empatía, amabilidad"],
["CAR","Carga de trabajo","cantidad de tarea, lectura o trabajo"],["RIG","Rigor de calificación","nivel de exigencia al calificar"],
["ORG","Organización / proyectos","orden del curso, plazos, proyectos"],["CLI","Clima de aula","ambiente, humor, respeto"],
["ASI","Asistencia / formato","asistencia, quizzes sorpresa, puntos extra, participación"]];
if(SOLO){ASP=ASP.filter(a=>a[0]===SOLO);document.getElementById("bannerSolo").style.display="";document.getElementById("bannerDenso").style.display="none"}
let items=[], idx=0, sel=null, filtro="todos", cur={};   // cur: {asp:{COD:'+'|'-'|'0'}, ninguno:bool}
const $=s=>document.querySelector(s);

function parse(t){const o={asp:{},ninguno:false};t=(t||"").trim();if(t==="ninguno"){o.ninguno=true;return o}
 t.split(/\s+/).filter(Boolean).forEach(x=>{const m=/^([A-Z]{3})([+\-0])$/.exec(x);if(m)o.asp[m[1]]=m[2]});return o}
function serializar(o){if(o.ninguno)return"ninguno";return ASP.map(a=>a[0]).filter(c=>o.asp[c]).map(c=>c+o.asp[c]).join(" ")}
const hecho=it=>(it.anot||"").trim()!=="";
function visibles(){return items.map((it,i)=>i).filter(i=>filtro==="todos"||!hecho(items[i]))}

async function guardar(){
  const it=items[idx], a=serializar(cur); it.anot=a;
  try{const r=await fetch("/api/guardar",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:TOKEN,review_id:it.id,anotacion:a})});
    if(!r.ok)throw new Error(await r.text());$("#estado").textContent="Guardado ✓";$("#estado").className=""}
  catch(e){$("#estado").textContent="NO SE GUARDÓ: "+e.message;$("#estado").className="err"}
  progreso();$("#actual").textContent=a||"(sin anotar)";
}
function progreso(){const n=items.filter(hecho).length;$("#prog").textContent=`${n} de ${items.length} anotados (${Math.round(100*n/Math.max(1,items.length))}%) · quedan ${items.length-n}`;$("#barra").style.width=(100*n/Math.max(1,items.length))+"%"}
function pinta(){
  const it=items[idx]; cur=parse(it.anot);
  $("#vista").innerHTML=`<div class="card"><div class="meta"><span>Comentario ${idx+1} de ${items.length} · id ${it.id}</span><span id="estado"></span></div>
   <p id="texto"></p></div>
   <div class="card" id="filas"></div>
   <div class="acciones"><button id="ant">← Anterior</button><button id="nin">${SOLO?"No es "+ASP[0][1].split(" ")[0]+" (n)":"Sin aspectos (n)"}</button><button id="borra">Borrar (c)</button><button id="sig">Siguiente →</button></div>
   <p class="actual">Anotación: <span id="actual"></span></p>`;
  $("#texto").textContent=it.texto;
  $("#filas").innerHTML=ASP.map((a,i)=>`<div class="fila" data-c="${a[0]}"><div class="k">${i+1}</div><div class="n"><b>${a[0]}</b>${a[1]}<div class="h">${a[2]}</div></div>
    <div class="sg"><button class="p" data-s="+">+</button><button class="z" data-s="0">0</button><button class="m" data-s="-">−</button></div></div>`).join("");
  $("#filas").onclick=e=>{const f=e.target.closest(".fila");if(!f)return;sel=f.dataset.c;const b=e.target.closest("[data-s]");if(b)fijar(sel,b.dataset.s);else refrescar()};
  $("#ant").onclick=()=>mover(-1);$("#sig").onclick=()=>mover(1);$("#nin").onclick=ninguno;$("#borra").onclick=borrar;
  if(SOLO)sel=SOLO;
  refrescar();progreso();$("#actual").textContent=it.anot||"(sin anotar)";
}
function refrescar(){document.querySelectorAll(".fila").forEach(f=>{const c=f.dataset.c,s=cur.asp[c];f.classList.toggle("sel",sel===c);
  f.querySelectorAll("[data-s]").forEach(b=>b.classList.toggle("on",s===b.dataset.s))});
  $("#nin").classList.toggle("on",cur.ninguno)}
function fijar(c,s){cur.ninguno=false;if(cur.asp[c]===s)delete cur.asp[c];else cur.asp[c]=s;refrescar();guardar()}
function ninguno(){const v=!cur.ninguno;cur={asp:{},ninguno:v};refrescar();guardar()}
function borrar(){cur={asp:{},ninguno:false};refrescar();guardar()}
function mover(d){const v=visibles();if(!v.length)return;let pos=v.indexOf(idx);if(SOLO)sel=SOLO;
  if(pos<0){pos=v.findIndex(i=>(d>0?i>idx:i<idx));if(pos<0)pos=d>0?v.length-1:0;idx=v[pos];sel=null;return pinta()}
  pos=Math.min(v.length-1,Math.max(0,pos+d));idx=v[pos];sel=null;pinta()}
function sigPend(){for(let k=1;k<=items.length;k++){const i=(idx+k)%items.length;if(!hecho(items[i])){idx=i;sel=null;return pinta()}}
  $("#vista").innerHTML='<div class="card fin">Todos los comentarios están anotados. ✓<br><small>Cierra con Ctrl+C en la terminal.</small></div>'}
function setFiltro(f){filtro=f;$("#fTodos").classList.toggle("on",f==="todos");$("#fPend").classList.toggle("on",f==="pend");
  const v=visibles();if(v.length&&!v.includes(idx)){idx=v[0]}if(!v.length)return sigPend();pinta()}
$("#fTodos").onclick=()=>setFiltro("todos");$("#fPend").onclick=()=>setFiltro("pend");$("#sigPend").onclick=sigPend;
document.addEventListener("keydown",e=>{if(e.ctrlKey||e.metaKey||e.altKey||!items.length||!$("#texto"))return;const k=e.key;
  if(/^[1-9]$/.test(k)){sel=ASP[+k-1][0];refrescar()}
  else if(sel&&(k==="+"||k==="="))fijar(sel,"+");else if(sel&&(k==="-"||k==="−"))fijar(sel,"-");else if(sel&&k==="0")fijar(sel,"0");
  else if(k==="n")ninguno();else if(k==="c")borrar();else if(k==="p")sigPend();
  else if(k==="ArrowRight"||k==="Enter"){e.preventDefault();mover(1)}else if(k==="ArrowLeft"){e.preventDefault();mover(-1)}});
(async()=>{const r=await fetch("/api/items?token="+TOKEN);if(!r.ok){$("#vista").textContent="Token inválido: recarga desde la terminal.";return}
  items=await r.json();document.title="Anotar gold · "+(SOLO?"solo "+SOLO:COLUMNA);idx=Math.max(0,items.findIndex(i=>!hecho(i)));pinta()})();
</script></body></html>
"""


def crear_servidor(gold, token, puerto, solo=""):
    pagina = PAGINA.replace("__TOKEN__", token).replace("__COLUMNA__", gold.columna).replace("__SOLO__", solo).encode("utf-8")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _responder(self, codigo, cuerpo, tipo="application/json"):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo + "; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                return self._responder(200, pagina, "text/html")
            if u.path == "/api/items":
                if parse_qs(u.query).get("token", [""])[0] != token:
                    return self._responder(403, b'"token"')
                return self._responder(200, json.dumps(gold.items(), ensure_ascii=False).encode("utf-8"))
            self._responder(404, b"no encontrado", "text/plain")

        def do_POST(self):
            if urlparse(self.path).path != "/api/guardar":
                return self._responder(404, b"no encontrado", "text/plain")
            try:
                datos = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                rid, anot = str(datos["review_id"]), datos["anotacion"]
                if datos.get("token") != token:
                    return self._responder(403, "token inválido".encode("utf-8"), "text/plain")
                if rid not in gold.indice:
                    return self._responder(400, "review_id desconocido".encode("utf-8"), "text/plain")
                if not isinstance(anot, str) or not anotacion_valida(anot) or (solo and anot not in ("", "ninguno") and not re.fullmatch(solo + r"[+\-0]", anot)):
                    return self._responder(400, "anotación inválida".encode("utf-8"), "text/plain")
                gold.guardar(rid, anot)
            except (ValueError, KeyError):
                return self._responder(400, "petición inválida".encode("utf-8"), "text/plain")
            self._responder(200, b'"ok"')

    return ThreadingHTTPServer(("127.0.0.1", puerto), H)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gold", default="data/gold_para_anotar.csv")
    ap.add_argument("--columna", default="anotacion", help="'anotacion' (tú) o 'anotacion_2' (segunda persona)")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--no-abrir", action="store_true", help="no abrir el navegador automáticamente")
    ap.add_argument("--solo", default="", choices=[""] + CODIGOS, help="re-anotar solo el signo de un aspecto (p. ej. RIG; ver absa_baseline.py preparar-aspecto)")
    a = ap.parse_args()
    if not Path(a.gold).exists():
        sys.exit(f"No existe {a.gold}. Corre el comando desde la carpeta del proyecto.")
    gold = Gold(a.gold, a.columna)
    token = secrets.token_urlsafe(16)
    srv = crear_servidor(gold, token, a.puerto, a.solo)
    url = f"http://127.0.0.1:{a.puerto}/"
    hechas, total = gold.resumen()
    print(f"Anotando {a.gold} (columna '{a.columna}'): {hechas}/{total} ya anotados. Copia del original: {a.gold}.bak")
    print(f"Abre {url}   (Ctrl+C para terminar)")
    if not a.no_abrir:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    hechas, total = gold.resumen()
    print(f"\nGuardado: {hechas}/{total} anotados.")
    if hechas == total and a.solo:
        print(f"Completo. Siguiente: python absa_baseline.py fusionar-aspecto --aspecto {a.solo} --parcial {a.gold}")
    elif hechas == total:
        print("Completo. Siguiente: python absa_baseline.py evaluar --gold " + a.gold + " --conjunto dev --json metricas/metricas_dev.json")


if __name__ == "__main__":
    main()
