"""Registro local de cada peça fatiada, sem depender de nenhum outro programa.

    python registro.py listar
    python registro.py linha [--id A02]
    python registro.py adicionar <peca>.gcode.3mf [--modelador fusion] [--documento "Nome"]

Uma linha JSON por fatiamento em registro.jsonl, ao lado da configuração. O fatiar.py
grava sozinho; `adicionar` é para quem fatiou à mão. Refatiar a mesma peça mantém o id e
acrescenta linha: na leitura vale a última.

Tempo e gramas só entram lidos do fatiado. Não existe caminho para digitar esses números.

Códigos de saída: 0 ok, 2 entrada inválida. Stdlib pura.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import bambu_3mf
import config as cfg


def caminho_registro(config=None):
    return (config or cfg.caminho_config()).with_name("registro.jsonl")


def ler(arquivo=None):
    """({id: última entrada}, avisos). Linha corrompida é pulada, nunca derruba a leitura."""
    arquivo = arquivo or caminho_registro()
    pecas, avisos = {}, []
    if not arquivo.is_file():
        return pecas, avisos
    linhas = arquivo.read_text(encoding="utf-8-sig").splitlines()
    for numero, linha in enumerate(linhas, 1):
        if not linha.strip():
            continue
        try:
            entrada = json.loads(linha)
            pecas[entrada["id"]] = entrada
        except (KeyError, TypeError, ValueError):
            avisos.append(f"registro.jsonl: linha {numero} ignorada")
    return pecas, avisos


def _id_da_peca(peca, pecas, prefixo):
    for entrada in pecas.values():
        if entrada.get("peca") == peca:
            return entrada["id"]
    padrao = re.compile(rf"^{re.escape(prefixo)}(\d+)$")
    achados = (padrao.match(i) for i in pecas)
    maior = max((int(m.group(1)) for m in achados if m), default=0)
    return f"{prefixo}{maior + 1:02d}"


def anotar(relatorio, peca, origem, config, *, modelador=None, documento=None, arquivo=None):
    """Acrescenta uma linha a partir do relatório do fatiamento. Devolve {id, arquivo}."""
    arquivo = arquivo or caminho_registro()
    pecas, _ = ler(arquivo)
    entrada = {
        "v": 1,
        "id": _id_da_peca(peca, pecas, config["registro"]["prefixo_id"]),
        "peca": peca,
        "data": datetime.now().astimezone().isoformat(timespec="seconds"),
        "medidas_mm": relatorio.get("dimensoes_mm"),
        "cores": [
            {"slot": f["slot"], "cor": f["cor"], "g": f["g"]} for f in relatorio["filamentos"]
        ],
        "peso_g": relatorio["peso_g"],
        "tempo_s": relatorio["tempo_s"],
        "camadas": relatorio["camadas"],
        "camada_mm": relatorio["camada_mm"],
        "arquivo": str(origem) if origem else None,
        "fatiado": relatorio["arquivo"],
        "modelador": modelador,
        "documento": documento,
        "maquina": config["maquina"]["modelo"],
    }
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("a", encoding="utf-8") as saida:
        saida.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    return {"id": entrada["id"], "arquivo": str(arquivo)}


def _relatorio_do_fatiado(fatiado):
    resumo = bambu_3mf.ler_3mf(fatiado)
    if not resumo.fatiado:
        raise ValueError(f"{fatiado} não é um arquivo fatiado")
    return {
        "arquivo": str(fatiado),
        "tempo_s": resumo.tempo_estimado_s,
        "peso_g": resumo.peso_g,
        "camadas": resumo.camadas_total,
        "camada_mm": resumo.camada_mm,
        "filamentos": [
            {"slot": f"slot{f.slot}", "cor": f.cor_hex, "g": f.usado_g} for f in resumo.filamentos
        ],
    }


def _virgula(valor, casas):
    return f"{valor:.{casas}f}".replace(".", ",")


def _tempo(segundos):
    if segundos is None:
        return "?"
    horas, minutos = segundos // 3600, segundos % 3600 // 60
    return f"{_virgula(segundos / 3600, 2)} ({horas}h{minutos:02d})"


def linha_markdown(entrada):
    """Linha da tabela: ID, peça, medidas, cores, peso, tempo, arquivo e data."""
    medidas = entrada.get("medidas_mm")
    cores = entrada["cores"]
    arquivo = f"`{entrada['arquivo'] or entrada['fatiado']}`"
    if entrada.get("documento"):
        origem = (entrada.get("modelador") or "modelador").capitalize()
        arquivo += f" · {origem}: *{entrada['documento']}*"
    colunas = [
        entrada["id"],
        entrada["peca"],
        " × ".join(_virgula(v, 2) for v in medidas) if medidas else "?",
        f"{len(cores)} — " + ", ".join(c["cor"] for c in cores),
        _virgula(entrada["peso_g"], 1) if entrada["peso_g"] is not None else "?",
        _tempo(entrada["tempo_s"]),
        arquivo,
        datetime.fromisoformat(entrada["data"]).strftime("%d/%m/%Y"),
    ]
    return "| " + " | ".join(str(c) for c in colunas) + " |"


def _nome_da_peca(fatiado):
    return Path(fatiado).name.removesuffix(".3mf").removesuffix(".gcode")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("listar")
    p_linha = comandos.add_parser("linha")
    p_linha.add_argument("--id")
    p_adicionar = comandos.add_parser("adicionar")
    p_adicionar.add_argument("fatiado")
    p_adicionar.add_argument("--modelador")
    p_adicionar.add_argument("--documento")
    args = parser.parse_args(argv)

    config = cfg.carregar()
    if args.comando == "adicionar":
        try:
            relatorio = _relatorio_do_fatiado(args.fatiado)
        except ValueError as erro:
            cfg.imprimir_json({"erro": str(erro)})
            return 2
        cfg.imprimir_json(anotar(relatorio, _nome_da_peca(args.fatiado), None, config,
                                 modelador=args.modelador, documento=args.documento))
        return 0

    pecas, avisos = ler()
    if args.comando == "listar":
        cfg.imprimir_json({"arquivo": str(caminho_registro()), "pecas": list(pecas.values()),
                           "avisos": avisos})
        return 0
    entrada = pecas.get(args.id) if args.id else next(reversed(pecas.values()), None)
    if entrada is None:
        cfg.imprimir_json({"erro": f"nada no registro para {args.id or 'a última peça'}"})
        return 2
    cfg.imprimir_json({"id": entrada["id"], "linha": linha_markdown(entrada),
                       "nota": config["registro"]["nota"], "secao": config["registro"]["secao"],
                       "avisos": avisos})
    return 0


if __name__ == "__main__":
    sys.exit(main())
