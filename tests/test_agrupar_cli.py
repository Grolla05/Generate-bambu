"""CLI do passo 3, rodado como o agente roda: subprocesso, stdout em JSON e código de saída."""

import json
import os
import subprocess
import sys
import zipfile

import pytest
from conftest import SKILL
from test_agrupar_3mf import _corpo, _escrever_3mf, _ler_modelo

SCRIPT = SKILL / "scripts" / "agrupar.py"


def _rodar(*args, codificacao="utf-8"):
    env = {**os.environ, "PYTHONIOENCODING": codificacao}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True, env=env, timeout=30, check=False,
    )


def _json(processo):
    return json.loads(processo.stdout.decode("utf-8"))


@pytest.fixture
def bruto(tmp_path):
    return _escrever_3mf(tmp_path / "peça bruta.3mf", [
        _corpo(1, "slot1_base", 0, 10),
        _corpo(2, "slot2_texto_A", 1, 2),
    ])


def test_agrupa_e_devolve_relatorio(bruto, tmp_path):
    final = tmp_path / "final.3mf"

    processo = _rodar(bruto, final)

    assert processo.returncode == 0, processo.stderr
    assert [o["slot"] for o in _json(processo)["objetos"]] == ["slot1", "slot2"]
    assert len(_ler_modelo(final)[0].findall(".//{*}object")) == 2
    assert bruto.is_file()


def test_cria_a_pasta_do_arquivo_final(bruto, tmp_path):
    final = tmp_path / "saída" / "peças" / "final.3mf"

    assert _rodar(bruto, final).returncode == 0
    assert final.is_file()


def test_apagar_bruto_so_depois_do_sucesso(bruto, tmp_path):
    assert _rodar(bruto, tmp_path / "final.3mf", "--apagar-bruto").returncode == 0
    assert not bruto.exists()


def test_recusa_preserva_o_bruto(tmp_path):
    bruto = _escrever_3mf(tmp_path / "bruto.3mf", [_corpo(1, "Body1", 0, 1)])

    processo = _rodar(bruto, tmp_path / "final.3mf", "--apagar-bruto")

    assert processo.returncode == 2
    assert "sem prefixo" in _json(processo)["erro"]
    assert bruto.is_file()
    assert not (tmp_path / "final.3mf").exists()


def test_apagar_bruto_nao_apaga_o_proprio_final(bruto):
    assert _rodar(bruto, bruto, "--apagar-bruto").returncode == 0
    assert bruto.is_file()


def test_limite_de_slots_na_linha_de_comando(bruto, tmp_path):
    processo = _rodar(bruto, tmp_path / "final.3mf", "--slots", "1")

    assert processo.returncode == 2
    assert "fora de 1 a 1" in _json(processo)["erro"]


def test_stdout_e_utf8_em_console_cp1252(tmp_path):
    bruto = _escrever_3mf(tmp_path / "bruto.3mf", [_corpo(1, "Corpo não nomeado", 0, 1)])

    processo = _rodar(bruto, tmp_path / "final.3mf", codificacao="cp1252")

    assert "não nomeado" in _json(processo)["erro"]


@pytest.mark.parametrize("conteudo", [b"isto nao e zip", None])
def test_arquivo_ruim_vira_erro_em_json(tmp_path, conteudo):
    bruto = tmp_path / "ruim.3mf"
    if conteudo:
        bruto.write_bytes(conteudo)

    processo = _rodar(bruto, tmp_path / "final.3mf")

    assert processo.returncode == 2
    assert _json(processo)["erro"]


def test_zip_sem_modelo_vira_erro_em_json(tmp_path):
    bruto = tmp_path / "vazio.3mf"
    with zipfile.ZipFile(bruto, "w") as z:
        z.writestr("outro.txt", "x")

    processo = _rodar(bruto, tmp_path / "final.3mf")

    assert processo.returncode == 2
    assert _json(processo)["erro"]


def test_modelo_com_xml_quebrado_vira_erro_em_json(tmp_path):
    bruto = tmp_path / "quebrado.3mf"
    with zipfile.ZipFile(bruto, "w") as z:
        z.writestr("3D/3dmodel.model", "<model")

    assert _rodar(bruto, tmp_path / "final.3mf").returncode == 2
