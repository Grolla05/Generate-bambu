"""Testa o diagnóstico do passo 0 contra um servidor HTTP local falso."""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import config as cfg
import diagnostico as dg
import pytest

INICIALIZADO = {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "fusion"}}}


@pytest.fixture
def servidor():
    resposta = {"status": 200, "corpo": b"", "tipo": "application/json", "pedidos": []}

    class Tratador(BaseHTTPRequestHandler):
        def do_POST(self):
            tamanho = int(self.headers["Content-Length"])
            resposta["pedidos"].append(json.loads(self.rfile.read(tamanho)))
            self.send_response(resposta["status"])
            self.send_header("Content-Type", resposta["tipo"])
            self.end_headers()
            self.wfile.write(resposta["corpo"])

        def log_message(self, *args):
            pass

    http = HTTPServer(("127.0.0.1", 0), Tratador)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    resposta["url"] = f"http://127.0.0.1:{http.server_port}/mcp"
    yield resposta
    http.shutdown()
    http.server_close()


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_mcp_respondendo_em_json(servidor):
    servidor["corpo"] = json.dumps(INICIALIZADO).encode()

    r = dg.testar_mcp(servidor["url"])

    assert r == {"estado": "respondendo", "servidor": {"name": "fusion"}}
    assert servidor["pedidos"][0]["method"] == "initialize"


def test_mcp_respondendo_em_sse(servidor):
    servidor["tipo"] = "text/event-stream"
    servidor["corpo"] = b"event: message\ndata: " + json.dumps(INICIALIZADO).encode() + b"\n\n"

    assert dg.testar_mcp(servidor["url"])["estado"] == "respondendo"


def test_porta_fechada():
    r = dg.testar_mcp(f"http://127.0.0.1:{_porta_livre()}/mcp", timeout=1)

    assert r["estado"] == "porta_fechada"


@pytest.mark.parametrize(
    "status, corpo",
    [(404, b"nada"), (200, b"<html>outra coisa</html>"), (200, b'{"result": {}}')],
)
def test_porta_aberta_sem_mcp(servidor, status, corpo):
    servidor["status"], servidor["corpo"] = status, corpo

    assert dg.testar_mcp(servidor["url"])["estado"] == "sem_mcp"


def _config(**bambu):
    config = json.loads(json.dumps(cfg.PADRAO))
    config["bambu_studio"].update(bambu)
    return config


def test_exe_da_config_vem_primeiro(tmp_path):
    exe = tmp_path / "bambu-studio.exe"
    exe.touch()

    r = dg.achar_bambu_studio(_config(exe=str(exe)))

    assert r == {"exe": str(exe), "versao": None, "origem": "config"}


def test_exe_configurado_que_nao_existe_e_erro(tmp_path):
    r = dg.achar_bambu_studio(_config(exe=str(tmp_path / "x.exe")))

    assert r["exe"] is None
    assert "não existe" in r["erro"]


def test_exe_vem_do_registro_fora_do_caminho_padrao(tmp_path, monkeypatch):
    exe = tmp_path / "bambu-studio.exe"
    exe.touch()
    monkeypatch.setattr(dg.shutil, "which", lambda _: None)

    r = dg.achar_bambu_studio(_config(), registro=lambda: (str(exe), "02.08.03.66"))

    assert r == {"exe": str(exe), "versao": "02.08.03.66", "origem": "registro"}


def test_sem_bambu_studio(monkeypatch):
    monkeypatch.setattr(dg.shutil, "which", lambda _: None)
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert dg.achar_bambu_studio(_config(), registro=lambda: (None, None))["exe"] is None


def test_diagnostico_mostra_maquina_e_perfil(tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATE_BAMBU_CONFIG", str(tmp_path / "config.json"))
    config = _config()

    def sem_fusion(_):
        return {"estado": "porta_fechada", "detalhe": "x"}

    def sem_bambu(_):
        return {"exe": None, "versao": None, "origem": None}

    r = dg.diagnosticar(config, testar=sem_fusion, achar=sem_bambu)

    assert r["maquina"]["modelo"] == "A1"
    assert r["impressao_testada"] is True
    assert r["perfil"]["existe"] is False

    config["maquina"]["modelo"] = "P1S"

    r = dg.diagnosticar(config, testar=sem_fusion, achar=sem_bambu)

    assert r["impressao_testada"] is False


def test_diagnostico_junta_tudo(tmp_path):
    config = _config()
    config["pasta_saida"] = str(tmp_path)

    r = dg.diagnosticar(
        config,
        testar=lambda _: {"estado": "porta_fechada", "detalhe": "x"},
        achar=lambda _: {"exe": "b.exe", "versao": None, "origem": "path"},
    )

    assert "Fusion MCP Server" in r["fusion"]["instrucao"]
    assert r["pasta_saida"]["existe"] is True
    assert r["fatiar_por_cli"] is True
