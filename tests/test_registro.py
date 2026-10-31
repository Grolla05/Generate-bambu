"""Registro local das peças, sempre em pasta temporária."""

import json
import zipfile

import bambu_3mf
import config as cfg
import fatiar as ft
import pytest
import registro as rg

RELATORIO = {
    "arquivo": "D:/saida/_fatiados/chaveiro/chaveiro.gcode.3mf",
    "tempo_s": 6060,
    "peso_g": 36.1,
    "camadas": 73,
    "camada_mm": 0.12,
    "dimensoes_mm": [51.0, 90.0, 8.76],
    "filamentos": [
        {"slot": "slot1", "cor": "#8B5A2B", "g": 20.0},
        {"slot": "slot2", "cor": "#F3E6C8", "g": 16.1},
    ],
    "avisos": [],
}


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATE_BAMBU_CONFIG", str(tmp_path / "config.json"))


@pytest.fixture
def config():
    return json.loads(json.dumps(cfg.PADRAO))


def _anotar(config, peca="chaveiro", **extras):
    return rg.anotar(RELATORIO, peca, "D:/saida/chaveiro.3mf", config, **extras)


def test_registro_fica_ao_lado_da_config(tmp_path):
    assert rg.caminho_registro() == tmp_path / "registro.jsonl"


def test_primeira_peca_vira_a01(config):
    assert _anotar(config)["id"] == "A01"

    entrada = rg.ler()[0]["A01"]
    assert entrada["peca"] == "chaveiro"
    assert entrada["peso_g"] == 36.1
    assert entrada["maquina"] == "A1"
    assert entrada["cores"][1] == {"slot": "slot2", "cor": "#F3E6C8", "g": 16.1}


def test_ids_sobem_a_partir_do_maior(config):
    _anotar(config, "um")
    _anotar(config, "dois")

    assert _anotar(config, "tres")["id"] == "A03"


def test_prefixo_vem_da_configuracao(config):
    config["registro"]["prefixo_id"] = "X"

    assert _anotar(config)["id"] == "X01"


def test_refatiar_mantem_o_id_e_vale_a_ultima(config):
    _anotar(config)
    rg.anotar({**RELATORIO, "peso_g": 40.0}, "chaveiro", None, config)

    pecas, _ = rg.ler()

    assert list(pecas) == ["A01"]
    assert pecas["A01"]["peso_g"] == 40.0
    assert len(rg.caminho_registro().read_text(encoding="utf-8").splitlines()) == 2


def test_linha_corrompida_e_pulada(config):
    _anotar(config)
    with rg.caminho_registro().open("a", encoding="utf-8") as saida:
        saida.write("{quebrado\n\n[1]\n")
    _anotar(config, "dois")

    pecas, avisos = rg.ler()

    assert list(pecas) == ["A01", "A02"]
    assert len(avisos) == 2


def test_sem_arquivo_nao_e_erro():
    assert rg.ler() == ({}, [])


def test_linha_markdown(config):
    _anotar(config, modelador="fusion", documento="Chaveiro Ana")

    linha = rg.linha_markdown(rg.ler()[0]["A01"])

    assert linha.startswith("| A01 | chaveiro | 51,00 × 90,00 × 8,76 | 2 — #8B5A2B, #F3E6C8 |")
    assert "| 36,1 | 1,68 (1h41) |" in linha
    assert "`D:/saida/chaveiro.3mf` · Fusion: *Chaveiro Ana*" in linha


def test_linha_markdown_sem_medidas_nem_documento(config):
    rg.anotar({**RELATORIO, "dimensoes_mm": None, "tempo_s": None}, "x", None, config)

    linha = rg.linha_markdown(rg.ler()[0]["A01"])

    assert "| x | ? |" in linha
    assert RELATORIO["arquivo"] in linha
    assert "Fusion" not in linha


def _fatiado(caminho):
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("Metadata/project_settings.config", json.dumps({"layer_height": "0.12"}))
        z.writestr(
            "Metadata/slice_info.config",
            '<config><plate><metadata key="prediction" value="1800"/>'
            '<metadata key="weight" value="4.20"/>'
            '<filament id="1" type="PLA" color="#112233" used_m="1" used_g="4.2"/>'
            '<layer_filament_lists><layer_filament_list filament_list="0" layer_ranges="0 23"/>'
            "</layer_filament_lists></plate></config>",
        )
    return caminho


def test_adicionar_le_os_numeros_do_fatiado(tmp_path, capsys):
    fatiado = _fatiado(tmp_path / "porta-copo.gcode.3mf")

    assert rg.main(["adicionar", str(fatiado), "--modelador", "blender"]) == 0

    assert json.loads(capsys.readouterr().out)["id"] == "A01"
    entrada = rg.ler()[0]["A01"]
    assert entrada["peca"] == "porta-copo"
    assert entrada["tempo_s"] == 1800
    assert entrada["peso_g"] == 4.2
    assert entrada["camadas"] == 24
    assert entrada["cores"] == [{"slot": "slot1", "cor": "#112233", "g": 4.2}]
    assert entrada["modelador"] == "blender"


def test_adicionar_recusa_arquivo_nao_fatiado(tmp_path, capsys):
    arquivo = tmp_path / "peca.3mf"
    with zipfile.ZipFile(arquivo, "w") as z:
        z.writestr("3D/3dmodel.model", "<model/>")

    assert rg.main(["adicionar", str(arquivo)]) == 2
    assert "não é um arquivo fatiado" in capsys.readouterr().out
    assert rg.ler() == ({}, [])


def test_adicionar_recusa_arquivo_ilegivel(tmp_path, capsys):
    assert rg.main(["adicionar", str(tmp_path / "nada.3mf")]) == 2
    assert "erro" in json.loads(capsys.readouterr().out)


def test_erro_3mf_e_value_error():
    # `main` depende disso para sair com código 2
    assert issubclass(bambu_3mf.Erro3mf, ValueError)


def test_comando_linha_traz_o_destino(config, capsys, monkeypatch):
    cfg.definir("registro.nota", "Catalogo.md")
    _anotar(config)

    assert rg.main(["linha"]) == 0

    saida = json.loads(capsys.readouterr().out)
    assert saida["id"] == "A01"
    assert saida["nota"] == "Catalogo.md"
    assert saida["linha"].startswith("| A01 |")


def test_comando_linha_com_id_desconhecido(config, capsys):
    _anotar(config)

    assert rg.main(["linha", "--id", "A99"]) == 2
    assert "A99" in capsys.readouterr().out


def test_comando_linha_sem_registro(capsys):
    assert rg.main(["linha"]) == 2
    assert "erro" in json.loads(capsys.readouterr().out)


def test_comando_listar(config, capsys):
    _anotar(config)

    assert rg.main(["listar"]) == 0

    assert json.loads(capsys.readouterr().out)["pecas"][0]["id"] == "A01"


def _preparar_main(monkeypatch, tmp_path):
    monkeypatch.setattr(ft.diagnostico, "achar_bambu_studio",
                        lambda _: {"exe": "x.exe", "versao": None, "origem": "config"})
    monkeypatch.setattr(ft, "processar", lambda *_: json.loads(json.dumps(RELATORIO)))
    return str(tmp_path / "chaveiro.3mf")


def test_fatiar_grava_sozinho(tmp_path, monkeypatch, capsys):
    entrada = _preparar_main(monkeypatch, tmp_path)

    assert ft.main([entrada, "--modelador", "fusion", "--documento", "Chaveiro"]) == 0

    saida = json.loads(capsys.readouterr().out)
    assert saida["registro"]["id"] == "A01"
    gravada = rg.ler()[0]["A01"]
    assert gravada["peca"] == "chaveiro"
    assert gravada["arquivo"] == entrada
    assert gravada["documento"] == "Chaveiro"


def test_falha_no_registro_nao_derruba_o_fatiamento(tmp_path, monkeypatch, capsys):
    entrada = _preparar_main(monkeypatch, tmp_path)

    def falhar(*_, **__):
        raise OSError("disco cheio")

    monkeypatch.setattr(ft.registro, "anotar", falhar)

    assert ft.main([entrada]) == 0

    saida = json.loads(capsys.readouterr().out)
    assert "registro" not in saida
    assert any("disco cheio" in a for a in saida["avisos"])
