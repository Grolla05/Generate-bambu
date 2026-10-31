"""Testa a configuração local da skill, sempre em pasta temporária."""

import json
import subprocess

import config as cfg
import pytest
from conftest import RAIZ, SKILL


@pytest.fixture(autouse=True)
def sem_ambiente(monkeypatch):
    monkeypatch.delenv("GENERATE_BAMBU_CONFIG", raising=False)
    monkeypatch.delenv("BAMBU_ACCESS_CODE", raising=False)


def test_exemplo_versionado_e_igual_ao_padrao():
    exemplo = json.loads((SKILL / "config.example.json").read_text(encoding="utf-8"))

    assert exemplo == cfg.PADRAO


def test_sem_arquivo_devolve_padroes(tmp_path):
    assert cfg.carregar(tmp_path / "config.json") == cfg.PADRAO


def test_arquivo_sobrepoe_sem_perder_chaves_novas(tmp_path):
    arquivo = tmp_path / "config.json"
    arquivo.write_text('{"bambu_studio": {"exe": "x.exe"}}', encoding="utf-8")

    config = cfg.carregar(arquivo)

    assert config["bambu_studio"]["exe"] == "x.exe"
    assert config["bambu_studio"]["processo"] == cfg.PADRAO["bambu_studio"]["processo"]


def test_ambiente_escolhe_o_arquivo(tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATE_BAMBU_CONFIG", str(tmp_path / "outro.json"))

    assert cfg.caminho_config() == tmp_path / "outro.json"


def test_definir_grava_chave_pontuada(tmp_path):
    arquivo = tmp_path / "pasta" / "config.json"

    cfg.definir("impressora.host", "192.0.2.10", arquivo)

    assert cfg.carregar(arquivo)["impressora"]["host"] == "192.0.2.10"


@pytest.mark.parametrize("chave", ["nada", "impressora.nada", "impressora", "versao.x"])
def test_definir_recusa_chave_desconhecida(tmp_path, chave):
    with pytest.raises(ValueError, match="desconhecida"):
        cfg.definir(chave, "x", tmp_path / "config.json")


def test_access_code_fica_fora_da_config(tmp_path):
    arquivo = tmp_path / "config.json"
    cfg.definir("impressora.serial", "ABC", arquivo)

    cfg.gravar_access_code("fixture-codigo", arquivo)

    assert "fixture-codigo" not in arquivo.read_text(encoding="utf-8")
    assert "fixture-codigo" not in json.dumps(cfg.mostrar(arquivo))
    assert cfg.mostrar(arquivo)["access_code_definido"] is True
    assert cfg.access_code(arquivo) == "fixture-codigo"


def test_access_code_do_ambiente_vence(tmp_path, monkeypatch):
    arquivo = tmp_path / "config.json"
    cfg.gravar_access_code("do-arquivo", arquivo)
    monkeypatch.setenv("BAMBU_ACCESS_CODE", "do-ambiente")

    assert cfg.access_code(arquivo) == "do-ambiente"


def test_config_com_bom_e_lida(tmp_path):
    arquivo = tmp_path / "config.json"
    arquivo.write_bytes(b'\xef\xbb\xbf{"pasta_saida": "D:/x"}')

    assert cfg.carregar(arquivo)["pasta_saida"] == "D:/x"


def test_comando_codigo_nao_ecoa(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GENERATE_BAMBU_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setattr(cfg.getpass, "getpass", lambda _: " fixture-codigo ")

    assert cfg.main(["codigo"]) == 0

    assert "fixture-codigo" not in capsys.readouterr().out
    assert cfg.access_code() == "fixture-codigo"


def test_nenhum_segredo_ou_config_local_versionado():
    arquivos = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.splitlines()

    nomes = {a.rsplit("/", 1)[-1] for a in arquivos}
    assert not nomes & {"config.json", "segredos.json", "config.local.json"}
