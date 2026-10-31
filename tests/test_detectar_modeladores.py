"""Testa a escolha do modelador: a tabela é o contrato do passo 0."""

import json

import config as cfg
import detectar_modeladores as dm
import pytest

casos = [
    # fusion, blender, tipo, preferido, conectado, usos, esperado
    (True, True, "preciso", "blender", False, {}, "fusion"),
    (True, False, "preciso", None, False, {}, "fusion"),
    (False, True, "preciso", None, False, {}, None),
    (True, True, "organico", "fusion", True, {}, "blender"),
    (True, False, "organico", None, False, {}, "fusion"),
    (False, True, "organico", None, False, {}, "blender"),
    (True, True, "qualquer", "blender", True, {}, "blender"),
    (True, True, "qualquer", None, True, {}, "fusion"),
    (True, True, "qualquer", None, False, {"fusion": 2, "blender": 1}, "fusion"),
    (True, True, "qualquer", None, False, {"fusion": 1, "blender": 2}, "blender"),
    (True, False, "qualquer", None, False, {}, "fusion"),
    (False, True, "qualquer", None, False, {}, "blender"),
]


@pytest.mark.parametrize("fusion, blender, tipo, preferido, conectado, usos, esperado", casos)
def test_tabela_de_escolha(fusion, blender, tipo, preferido, conectado, usos, esperado):
    r = dm.escolher(fusion, blender, tipo, preferido, conectado, usos)

    assert r["modelador"] == esperado
    assert r["motivo"]


def test_preciso_sem_fusion_nao_troca_em_silencio():
    r = dm.escolher(False, True, "preciso")

    assert r["modelador"] is None and r["perguntar"] is False
    assert "não troque" in r["motivo"]


def test_duvida_pergunta_uma_vez():
    r = dm.escolher(True, True, "qualquer", usos={"blender": 5})

    assert r["modelador"] is None and r["perguntar"] is True
    assert "modelador.preferido" in r["motivo"]


def test_nenhum_instalado():
    r = dm.escolher(False, False, "qualquer")

    assert r["modelador"] is None and r["perguntar"] is False


def _config(exe=None):
    config = json.loads(json.dumps(cfg.PADRAO))
    config["modelador"]["blender_exe"] = exe
    return config


def test_blender_da_config_vem_primeiro(tmp_path):
    exe = tmp_path / "blender.exe"
    exe.touch()

    assert dm.achar_blender(_config(str(exe))) == str(exe)


def test_blender_configurado_que_sumiu(tmp_path):
    assert dm.achar_blender(_config(str(tmp_path / "x.exe"))) is None


def test_blender_vem_da_busca(tmp_path, monkeypatch):
    exe = tmp_path / "blender.exe"
    exe.touch()
    monkeypatch.setattr(dm.shutil, "which", lambda _: None)

    assert dm.achar_blender(_config(), busca=(lambda: None, lambda: str(exe))) == str(exe)


def test_sem_blender(monkeypatch):
    monkeypatch.setattr(dm.shutil, "which", lambda _: None)

    assert dm.achar_blender(_config(), busca=()) is None


def test_fusion_fica_no_webdeploy(tmp_path, monkeypatch):
    exe = tmp_path / "Autodesk/webdeploy/production/abc/Fusion360.exe"
    exe.parent.mkdir(parents=True)
    exe.touch()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert dm.achar_fusion() == str(exe)


def test_uso_do_blender_vem_dos_recentes(tmp_path, monkeypatch):
    arquivo = tmp_path / "Blender Foundation/Blender/5.2/config/recent-files.txt"
    arquivo.parent.mkdir(parents=True)
    arquivo.touch()
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert dm.uso_blender() == arquivo.stat().st_mtime
