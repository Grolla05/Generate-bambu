"""Passo 0: o que está pronto nesta máquina, em JSON para o agente decidir.

Testa o MCP do Fusion com um `initialize` de verdade, porque porta aberta não prova
que o servidor certo responde, e procura o Bambu Studio, que pode ter sido instalado
fora do caminho padrão (o instalador deixa escolher a pasta).

    python diagnostico.py

Stdlib pura.
"""

import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

import config as cfg

TIMEOUT_S = 2.0
_INICIALIZAR = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "generate-bambu-diagnostico", "version": "1"},
    },
}
INSTRUCOES = {
    "respondendo": "",
    "porta_fechada": (
        "Fusion fechado ou servidor desligado: abra o Fusion e ligue Preferences → General → "
        "API → Fusion MCP Server, com Apply e depois OK."
    ),
    "sem_mcp": (
        "Algo responde nessa porta, mas não é o MCP do Fusion: confira fusion.url_mcp e o que "
        "está usando a porta."
    ),
}


def _json_da_resposta(corpo):
    """A resposta vem como JSON puro ou como evento SSE (`data: {...}`)."""
    texto = corpo.decode("utf-8", "replace").strip()
    if not texto.startswith("{"):
        linhas = [li[5:].strip() for li in texto.splitlines() if li.startswith("data:")]
        texto = linhas[0] if linhas else ""
    try:
        dados = json.loads(texto)
    except ValueError:
        return None
    return dados if isinstance(dados, dict) else None


def testar_mcp(url, timeout=TIMEOUT_S):
    pedido = urllib.request.Request(
        url,
        data=json.dumps(_INICIALIZAR).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    # Proxy do sistema não pode interceptar 127.0.0.1.
    abrir = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
    try:
        with abrir(pedido, timeout=timeout) as resposta:
            dados = _json_da_resposta(resposta.read())
    except urllib.error.HTTPError as erro:
        return {"estado": "sem_mcp", "detalhe": f"HTTP {erro.code}"}
    except (urllib.error.URLError, OSError) as erro:
        motivo = getattr(erro, "reason", erro)
        return {"estado": "porta_fechada", "detalhe": str(motivo)}
    resultado = (dados or {}).get("result")
    if not isinstance(resultado, dict) or "serverInfo" not in resultado:
        return {"estado": "sem_mcp", "detalhe": "resposta não é um initialize de MCP"}
    return {"estado": "respondendo", "servidor": resultado["serverInfo"]}


def _bambu_no_registro():
    """(exe, versão) da instalação registrada no Windows; o exe vem do DisplayIcon."""
    try:
        import winreg
    except ImportError:
        return None, None
    raizes = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for raiz, caminho in raizes:
        try:
            pai = winreg.OpenKey(raiz, caminho)
        except OSError:
            continue
        with pai:
            for i in range(winreg.QueryInfoKey(pai)[0]):
                try:
                    with winreg.OpenKey(pai, winreg.EnumKey(pai, i)) as chave:
                        if winreg.QueryValueEx(chave, "DisplayName")[0] != "Bambu Studio":
                            continue
                        icone = winreg.QueryValueEx(chave, "DisplayIcon")[0]
                        versao = winreg.QueryValueEx(chave, "DisplayVersion")[0]
                except OSError:
                    continue
                return icone.split(",")[0].strip('"'), versao
    return None, None


def achar_bambu_studio(config, registro=_bambu_no_registro):
    """Ordem: configuração → PATH → registro → pastas padrão. Devolve o que achou e de onde."""
    configurado = config["bambu_studio"]["exe"]
    if configurado:
        if Path(configurado).is_file():
            return {"exe": configurado, "versao": None, "origem": "config"}
        return {"exe": None, "versao": None, "origem": None,
                "erro": f"bambu_studio.exe não existe: {configurado}"}
    no_path = shutil.which("bambu-studio")
    if no_path:
        return {"exe": no_path, "versao": None, "origem": "path"}
    exe, versao = registro()
    if exe and Path(exe).is_file():
        return {"exe": exe, "versao": versao, "origem": "registro"}
    for base in filter(None, (os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA"))):
        for sub in ("", "Programs"):
            padrao = Path(base, sub, "Bambu Studio", "bambu-studio.exe")
            if padrao.is_file():
                return {"exe": str(padrao), "versao": None, "origem": "padrao"}
    return {"exe": None, "versao": None, "origem": None}


def diagnosticar(config, testar=testar_mcp, achar=achar_bambu_studio):
    fusion = testar(config["fusion"]["url_mcp"])
    fusion["instrucao"] = INSTRUCOES[fusion["estado"]]
    bambu = achar(config)
    pasta = config["pasta_saida"]
    modelo = config["maquina"]["modelo"]
    return {
        "fusion": fusion,
        "bambu_studio": bambu,
        "python": ".".join(map(str, sys.version_info[:3])),
        "pasta_saida": {"caminho": pasta, "existe": bool(pasta) and Path(pasta).is_dir()},
        "perfil": cfg.perfil(),
        "maquina": config["maquina"],
        "impressao_testada": modelo == cfg.MAQUINA_TESTADA,
        "fatiar_por_cli": bool(bambu["exe"]),
    }


def main():
    cfg.imprimir_json(diagnosticar(cfg.carregar()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
