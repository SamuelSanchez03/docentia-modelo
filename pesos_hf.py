#!/usr/bin/env python3
"""
pesos_hf.py - sube o baja los pesos del modelo a Hugging Face Hub (GitHub no admite archivos de más de 100 MB).

  python pesos_hf.py subir USUARIO/docentia-absa              # crea el repo de modelo (PRIVADO) y sube pesos + config + tokenizer
  python pesos_hf.py subir USUARIO/docentia-absa --publico    # igual, pero visible para todos
  python pesos_hf.py bajar USUARIO/docentia-absa              # deja data/modelos/v2b_roberta y data/modelos/v2b listos
  python pesos_hf.py bajar USUARIO/docentia-absa --version v2b_roberta

Para subir hace falta un token de Hugging Face con permiso de escritura: variable de entorno HF_TOKEN
o `hf auth login` (`huggingface-cli login` en versiones antiguas de huggingface_hub).
Para bajar de un repo privado también hace falta el token; de uno público, no.

No se sube checkpoint.pt (~1.4 GB): solo guarda el optimizador para reanudar un entrenamiento.
En el repo de Hugging Face cada versión queda en su carpeta (v2b_roberta/, v2b/), igual que en data/modelos/.
"""
import argparse
import sys
from pathlib import Path

VERSIONES = ["v2b_roberta", "v2b"]   # roberta-base (la elegida) y distilroberta-base
RAIZ = Path("data/modelos")
A_SUBIR = ["modelo.pt", "config.json", "tokenizer/*"]


def _hub():
    try:
        import huggingface_hub
    except ImportError:
        sys.exit("Falta huggingface_hub: pip install huggingface_hub")
    return huggingface_hub


def cmd_subir(a):
    api = _hub().HfApi()
    versiones = a.version or VERSIONES
    for v in versiones:
        if not (RAIZ / v / "modelo.pt").exists():
            sys.exit(f"No encuentro {RAIZ / v / 'modelo.pt'}")
    api.create_repo(a.repo, repo_type="model", private=not a.publico, exist_ok=True)
    for v in versiones:
        print(f"Subiendo {RAIZ / v} ...", flush=True)
        api.upload_folder(repo_id=a.repo, repo_type="model", folder_path=str(RAIZ / v), path_in_repo=v,
                          allow_patterns=A_SUBIR, commit_message=f"Pesos {v}")
    print(f"Listo: https://huggingface.co/{a.repo}")
    return 0


def cmd_bajar(a):
    versiones = a.version or VERSIONES
    _hub().snapshot_download(repo_id=a.repo, repo_type="model", local_dir=str(RAIZ),
                             allow_patterns=[f"{v}/*" for v in versiones])
    faltan = [v for v in versiones if not (RAIZ / v / "modelo.pt").exists()]
    for v in versiones:
        print(("FALTA " if v in faltan else "OK    ") + str(RAIZ / v / "modelo.pt"))
    return 1 if faltan else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nombre in ("subir", "bajar"):
        p = sub.add_parser(nombre)
        p.add_argument("repo", help="USUARIO/nombre del repo de modelo en Hugging Face")
        p.add_argument("--version", action="append", choices=VERSIONES, help="solo esta versión (repetible); por defecto, todas")
        if nombre == "subir":
            p.add_argument("--publico", action="store_true", help="crear el repo público (por defecto, privado)")
    a = ap.parse_args()
    sys.exit({"subir": cmd_subir, "bajar": cmd_bajar}[a.cmd](a))
