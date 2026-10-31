"""Configuração local da skill, guardada fora da pasta dela.

Atualizar o plugin troca a pasta da skill inteira: por isso tudo vive em
~/.generate-bambu/ (ou no arquivo de GENERATE_BAMBU_CONFIG). O access code da
impressora fica à parte, em segredos.json, para que ler ou mostrar a configuração
nunca exponha o código.

    python config.py mostrar
    python config.py definir bambu_studio.exe "D:/Bambu Studio/bambu-studio.exe"
    python config.py maquina "A1 mini"
    python config.py codigo        # rode você mesmo: pede o access code sem ecoar

O contexto de quem usa (negócio, licenças, onde registrar) fica em perfil.md, na mesma
pasta, e nunca no repositório.

Stdlib pura.
"""

import argparse
import copy
import getpass
import json
import os
import sys
from pathlib import Path

# Só a A1 imprimiu de verdade. As outras foram conferidas até o fatiamento.
MAQUINA_TESTADA = "A1"
MAQUINAS = {
    "A1": {
        "mesa_mm": 256, "limite_mm": 250, "slots": 4,
        "impressora": "Bambu Lab A1 0.4 nozzle",
        "processo": "0.12mm Fine @BBL A1",
        "filamento_padrao": "Bambu PLA Basic @BBL A1",
    },
    "A1 mini": {
        "mesa_mm": 180, "limite_mm": 175, "slots": 4,
        "impressora": "Bambu Lab A1 mini 0.4 nozzle",
        "processo": "0.12mm Fine @BBL A1M",
        "filamento_padrao": "Bambu PLA Basic @BBL A1M",
    },
    "P1S": {
        "mesa_mm": 256, "limite_mm": 250, "slots": 4,
        "impressora": "Bambu Lab P1S 0.4 nozzle",
        "processo": "0.12mm Fine @BBL P1P",
        "filamento_padrao": "Bambu PLA Basic @BBL P1S 0.4 nozzle",
    },
}
_CAMPOS_MAQUINA = ("mesa_mm", "limite_mm", "slots")
_CAMPOS_PERFIS = ("impressora", "processo", "filamento_padrao")

PADRAO = {
    "versao": 1,
    "pasta_saida": None,
    "fusion": {"projeto": "generate-bambu", "url_mcp": "http://127.0.0.1:27182/mcp"},
    "maquina": {"modelo": "A1", "mesa_mm": 256, "limite_mm": 250, "slots": 4},
    "bambu_studio": {
        "exe": None,
        "impressora": "Bambu Lab A1 0.4 nozzle",
        "processo": "0.12mm Fine @BBL A1",
        "filamento_padrao": "Bambu PLA Basic @BBL A1",
        "mesa": "Textured PEI Plate",
    },
    "impressora": {"host": None, "serial": None},
    "modelador": {"preferido": None, "blender_exe": None},
    "registro": {"prefixo_id": "A", "nota": None, "secao": None},
}


def caminho_config():
    env = os.environ.get("GENERATE_BAMBU_CONFIG")
    return Path(env) if env else Path.home() / ".generate-bambu" / "config.json"


def caminho_segredos(config=None):
    return (config or caminho_config()).with_name("segredos.json")


def caminho_perfil(config=None):
    return (config or caminho_config()).with_name("perfil.md")


def _mesclar(base, novo):
    for chave, valor in novo.items():
        if isinstance(valor, dict) and isinstance(base.get(chave), dict):
            _mesclar(base[chave], valor)
        else:
            base[chave] = valor
    return base


def _gravar(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def carregar(caminho=None):
    """Padrões sobrepostos pelo arquivo. Chave nova da skill aparece sem migrar nada."""
    caminho = caminho or caminho_config()
    config = copy.deepcopy(PADRAO)
    if caminho.is_file():
        _mesclar(config, json.loads(caminho.read_text(encoding="utf-8-sig")))
    return config


def definir(chave, valor, caminho=None):
    """Grava uma chave pontuada (`bambu_studio.exe`), recusando o que não existe no padrão."""
    caminho = caminho or caminho_config()
    config = carregar(caminho)
    alvo, modelo = config, PADRAO
    *grupos, final = chave.split(".")
    for grupo in grupos:
        if not isinstance(modelo.get(grupo), dict):
            raise ValueError(f"chave desconhecida: {chave}")
        alvo, modelo = alvo[grupo], modelo[grupo]
    if final not in modelo or isinstance(modelo[final], dict):
        raise ValueError(f"chave desconhecida: {chave}")
    if isinstance(modelo[final], int):
        try:
            valor = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"{chave} precisa ser número: {valor}") from erro
    alvo[final] = valor
    _gravar(caminho, config)
    return config


def escolher_maquina(nome, caminho=None):
    """Grava limites e perfis juntos: um sem o outro fatiaria na mesa errada."""
    if nome not in MAQUINAS:
        raise ValueError(f"máquina desconhecida: {nome}; use {', '.join(MAQUINAS)}")
    caminho = caminho or caminho_config()
    config = carregar(caminho)
    preset = MAQUINAS[nome]
    config["maquina"] = {"modelo": nome, **{k: preset[k] for k in _CAMPOS_MAQUINA}}
    config["bambu_studio"].update({k: preset[k] for k in _CAMPOS_PERFIS})
    _gravar(caminho, config)
    return config


def access_code(caminho=None):
    env = os.environ.get("BAMBU_ACCESS_CODE")
    if env:
        return env
    arquivo = caminho_segredos(caminho)
    if not arquivo.is_file():
        return None
    return json.loads(arquivo.read_text(encoding="utf-8-sig")).get("access_code")


def gravar_access_code(codigo, caminho=None):
    _gravar(caminho_segredos(caminho), {"access_code": codigo})


def perfil(caminho=None):
    arquivo = caminho_perfil(caminho)
    return {"caminho": str(arquivo), "existe": arquivo.is_file()}


def mostrar(caminho=None):
    return {
        "arquivo": str(caminho or caminho_config()),
        "config": carregar(caminho),
        "perfil": perfil(caminho),
        "access_code_definido": bool(access_code(caminho)),
    }


def imprimir_json(dados):
    """Saída dos scripts para o agente: JSON em UTF-8, mesmo em console cp1252."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(dados, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("mostrar")
    comandos.add_parser("codigo")
    p_definir = comandos.add_parser("definir")
    p_definir.add_argument("chave")
    p_definir.add_argument("valor")
    p_maquina = comandos.add_parser("maquina")
    p_maquina.add_argument("nome")
    args = parser.parse_args(argv)

    try:
        if args.comando == "definir":
            definir(args.chave, args.valor)
        elif args.comando == "maquina":
            escolher_maquina(args.nome)
    except ValueError as erro:
        print(erro, file=sys.stderr)
        return 2
    if args.comando == "codigo":
        gravar_access_code(getpass.getpass("Access code da impressora: ").strip())
        print(f"Gravado em {caminho_segredos()}")
        return 0
    imprimir_json(mostrar())
    return 0


if __name__ == "__main__":
    sys.exit(main())
