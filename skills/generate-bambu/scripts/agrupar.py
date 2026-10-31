"""Passo 3: agrupa o .3mf bruto do modelador, sem colar nada no script do Fusion.

    python agrupar.py <bruto>.3mf <final>.3mf [--slots N] [--apagar-bruto]

Devolve o relatório do helper em JSON. O bruto só é apagado depois do sucesso.

Códigos de saída: 0 ok, 2 entrada inválida.

O CLI mora aqui, e não em helpers/agrupar_3mf.py, porque aquele arquivo também é colado
no Fusion, onde pode rodar como __main__. Stdlib pura.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "helpers"))

import config as cfg  # noqa: E402
from agrupar_3mf import agrupar_por_slot  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bruto", help=".3mf que o modelador exportou")
    parser.add_argument("final", help=".3mf de um objeto por slot")
    parser.add_argument("--slots", type=int, help="slots da impressora; padrão: configuração")
    parser.add_argument("--apagar-bruto", action="store_true", help="apaga o bruto se der certo")
    args = parser.parse_args(argv)

    bruto, final = Path(args.bruto), Path(args.final)
    try:
        slots = args.slots or cfg.carregar()["maquina"]["slots"]
        final.parent.mkdir(parents=True, exist_ok=True)
        relatorio = agrupar_por_slot(str(bruto), str(final), max_slots=slots)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as erro:
        cfg.imprimir_json({"erro": str(erro)})
        return 2
    if args.apagar_bruto and bruto.resolve() != final.resolve():
        bruto.unlink()
    cfg.imprimir_json(relatorio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
