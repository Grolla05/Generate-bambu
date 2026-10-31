"""Passo 0: qual modelador usar nesta peça, e por quê.

    python detectar_modeladores.py --tipo preciso|organico|qualquer

O tipo vem da sua leitura do pedido. A decisão é de `escolher()`, uma função pura. Medida
exata é sempre Fusion, porque malha não tem parâmetros. Stdlib pura.

A porta do add-on do Blender não é documentada: o MCP se prova chamando a ferramenta
`get_objects_summary`, e sem ele o Blender roda por `--background`.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

import config as cfg
import diagnostico


def _blender_do_atalho():
    """O instalador .zip e o Steam não registram nada: o atalho é o que sobra."""
    pastas = [Path.home() / "Desktop", Path.home() / "OneDrive" / "Desktop"]
    if os.environ.get("APPDATA"):
        pastas.append(Path(os.environ["APPDATA"], "Microsoft/Windows/Start Menu/Programs"))
    atalhos = [str(a) for p in pastas if p.is_dir() for a in p.rglob("Blender*.lnk")]
    if not atalhos or not shutil.which("powershell.exe"):
        return None
    script = "(New-Object -ComObject WScript.Shell).CreateShortcut($env:ATALHO).TargetPath"
    resposta = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=15, check=False,
        env={**os.environ, "ATALHO": atalhos[0]},
    )
    alvo = resposta.stdout.strip()
    return str(Path(alvo).with_name("blender.exe")) if alvo else None


def _blender_nas_pastas():
    bases = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
    padroes = ("Blender Foundation/*/blender.exe", "Steam/steamapps/common/Blender/blender.exe")
    for base in filter(None, bases):
        for padrao in padroes:
            achados = sorted(glob.glob(str(Path(base, padrao))))
            if achados:
                return achados[-1]
    return None


def achar_blender(config, busca=(_blender_nas_pastas, _blender_do_atalho)):
    configurado = config["modelador"]["blender_exe"]
    if configurado:
        return configurado if Path(configurado).is_file() else None
    no_path = shutil.which("blender")
    if no_path:
        return no_path
    for procurar in busca:
        achado = procurar()
        if achado and Path(achado).is_file():
            return achado
    return None


def achar_fusion():
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        return None
    achados = glob.glob(str(Path(base, "Autodesk/webdeploy/production/*/Fusion360.exe")))
    return max(achados, key=os.path.getmtime) if achados else None


def uso_blender():
    """Data da lista de recentes da versão mais nova usada."""
    base = os.environ.get("APPDATA")
    if not base:
        return None
    arquivos = glob.glob(str(Path(base, "Blender Foundation/Blender/*/config/recent-files.txt")))
    return max((os.path.getmtime(a) for a in arquivos), default=None)


def escolher(fusion, blender, tipo, preferido=None, fusion_conectado=False, usos=None):
    """Devolve {modelador, motivo, perguntar}. modelador None quer dizer: pare ou pergunte."""
    usos = usos or {}
    if not fusion and not blender:
        return {"modelador": None, "perguntar": False,
                "motivo": "Nem Fusion nem Blender instalados: peça para instalar um."}
    if tipo == "preciso":
        if fusion:
            return {"modelador": "fusion", "perguntar": False,
                    "motivo": "Medida exata, rosca ou encaixe pedem geometria paramétrica."}
        return {"modelador": None, "perguntar": False,
                "motivo": "Peça de medida exata pede o Fusion, que não está instalado. "
                          "No Blender a malha não tem parâmetros: não troque em silêncio."}
    if tipo == "organico":
        if blender:
            return {"modelador": "blender", "perguntar": False,
                    "motivo": "Forma orgânica se modela melhor em malha."}
        return {"modelador": "fusion", "perguntar": False,
                "motivo": "Sem Blender: ofereça versão estilizada em camadas no Fusion."}
    if not blender or not fusion:
        modelador = "fusion" if fusion else "blender"
        return {"modelador": modelador, "perguntar": False,
                "motivo": f"Só o {modelador.capitalize()} está instalado."}
    if preferido in ("fusion", "blender"):
        return {"modelador": preferido, "perguntar": False, "motivo": "Preferência gravada."}
    if fusion_conectado:
        return {"modelador": "fusion", "perguntar": False,
                "motivo": "Serve nos dois, e o Fusion já está aberto e respondendo."}
    if usos.get("fusion") and usos.get("blender"):
        modelador = max(("fusion", "blender"), key=usos.get)
        return {"modelador": modelador, "perguntar": False, "motivo": "Foi o usado por último."}
    return {"modelador": None, "perguntar": True,
            "motivo": "Serve nos dois e não sei qual você prefere: pergunte uma vez e grave "
                      "em modelador.preferido."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tipo", choices=("preciso", "organico", "qualquer"), required=True)
    args = parser.parse_args(argv)

    config = cfg.carregar()
    fusion, blender = achar_fusion(), achar_blender(config)
    conectado = diagnostico.testar_mcp(config["fusion"]["url_mcp"])["estado"] == "respondendo"
    cfg.imprimir_json({
        "fusion": {"exe": fusion, "mcp_respondendo": conectado},
        "blender": {"exe": blender},
        "escolha": escolher(bool(fusion), bool(blender), args.tipo,
                            config["modelador"]["preferido"], conectado,
                            {"blender": uso_blender()}),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
