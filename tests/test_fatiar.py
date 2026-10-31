"""Testa o fatiamento com um executor falso, sem Bambu Studio."""

import json
import subprocess
import zipfile

import bambu_3mf
import config as cfg
import fatiar as ft
import perfis
import projeto_bambu as pb
import pytest
from agrupar_3mf import montar_3mf

CUBO = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0),
        (0, 0, 2), (10, 0, 2), (10, 10, 2), (0, 10, 2)]
TRIS = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
        (3, 7, 6), (3, 6, 2), (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5)]
SLICE_INFO = (
    '<config><plate><metadata key="index" value="1"/>'
    '<metadata key="prediction" value="2059"/><metadata key="weight" value="8.15"/>'
    '{warning}'
    '<filament id="1" type="PLA" color="#E8B647" used_m="1.46" used_g="4.43"/>'
    '<filament id="2" type="PLA" color="#1A73E8" used_m="0.73" used_g="{g2}"/>'
    '<layer_filament_lists><layer_filament_list filament_list="0" layer_ranges="0 23"/>'
    '</layer_filament_lists></plate></config>'
)


def _slot(nome, cor, x0=0.0):
    verts = [(x + x0, y, z) for x, y, z in CUBO]
    return {"slot": nome, "cor": cor, "verts": verts, "tris": TRIS, "corpos": [nome]}


@pytest.fixture
def perfis_bbl(tmp_path):
    raiz = tmp_path / "Bambu" / "resources" / "profiles" / "BBL"
    arquivos = {
        "machine/base.json": {"name": "base", "printable_height": "250"},
        "machine/inc.json": {"name": "inc", "machine_start_gcode": "G28"},
        "machine/a1.json": {"name": "A1", "inherits": "base", "include": ["inc"],
                            "type": "machine", "nozzle_diameter": ["0.4"]},
        "process/base.json": {"name": "pbase", "wall_loops": "2", "layer_height": "0.2"},
        "process/fina.json": {"name": "Fina", "inherits": "pbase", "layer_height": "0.12",
                              "compatible_printers": ["A1"]},
        "filament/pla.json": {"name": "PLA", "filament_id": "GFA00", "type": "filament",
                              "nozzle_temperature": ["220"], "filament_type": ["PLA"]},
    }
    for rel, dados in arquivos.items():
        caminho = raiz / rel
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json.dumps(dados), encoding="utf-8")
    return raiz


@pytest.fixture
def config():
    c = json.loads(json.dumps(cfg.PADRAO))
    c["bambu_studio"].update(impressora="A1", processo="Fina", filamento_padrao="PLA")
    return c


@pytest.fixture
def bambu(perfis_bbl):
    return {"exe": str(perfis_bbl.parents[2] / "bambu-studio.exe"), "versao": "02.08.03.66"}


@pytest.fixture
def entrada(tmp_path):
    arquivo = tmp_path / "chaveiro.3mf"
    slots = [_slot("slot1", "#E8B647FF"), _slot("slot2", "#1A73E8FF", 20)]
    montar_3mf(slots, str(arquivo))
    return arquivo


def executor(respostas=None, g2="2.20", warning="", largura=30.0):
    """Falso `subprocess.run`: grava o que o CLI gravaria e guarda os comandos."""
    respostas = list(respostas or [0])
    comandos = []

    def executar(comando, cwd, **_):
        comandos.append(comando)
        codigo = respostas.pop(0)
        (cwd / "result.json").write_text(json.dumps({
            "return_code": codigo, "error_string": "falhou",
            "sliced_plates": [{"objects": [{"bbox": {"width": largura, "depth": 10.0,
                                                     "height": 2.0}}]}],
        }), encoding="utf-8")
        if codigo == 0:
            with zipfile.ZipFile(cwd / "projeto.3mf") as z:
                ajustes = z.read("Metadata/project_settings.config")
            with zipfile.ZipFile(cwd / ft.ARQUIVO_FATIADO, "w") as z:
                z.writestr("Metadata/slice_info.config",
                           SLICE_INFO.format(g2=g2, warning=warning))
                z.writestr("Metadata/project_settings.config", ajustes)
        return subprocess.CompletedProcess(comando, 0)

    executar.comandos = comandos
    return executar


def test_fatia_e_devolve_relatorio(entrada, config, bambu):
    r = ft.processar(entrada, config, bambu, executar=executor())

    assert r["arquivo"].endswith("_fatiados\\chaveiro\\chaveiro.gcode.3mf") or r[
        "arquivo"
    ].endswith("_fatiados/chaveiro/chaveiro.gcode.3mf")
    assert r["tempo_s"] == 2059
    assert r["peso_g"] == 8.15
    assert r["camadas"] == 24
    assert r["camada_mm"] == 0.12
    assert r["dimensoes_mm"] == [30.0, 10.0, 2.0]
    assert r["filamentos"] == [{"slot": "slot1", "cor": "#E8B647", "g": 4.43},
                               {"slot": "slot2", "cor": "#1A73E8", "g": 2.2}]
    assert r["avisos"] == []


def test_so_sobra_o_fatiado_na_pasta(entrada, config, bambu):
    ft.processar(entrada, config, bambu, executar=executor())

    pasta = entrada.parent / "_fatiados" / "chaveiro"
    assert [p.name for p in pasta.iterdir()] == ["chaveiro.gcode.3mf"]


def test_comando_fatia_so_a_placa_um_sem_rearranjar(entrada, config, bambu):
    executar = executor()

    ft.processar(entrada, config, bambu, executar=executar)

    comando = executar.comandos[0]
    assert comando[comando.index("--slice") + 1] == "1"
    assert comando[comando.index("--arrange") + 1] == "0"


def test_comando_nunca_envia_para_impressora(entrada, config, bambu):
    executar = executor()

    ft.processar(entrada, config, bambu, executar=executar)

    texto = " ".join(executar.comandos[0]).lower()
    assert "--send" not in texto and "ftp" not in texto and "mqtt" not in texto


def test_torre_desce_quando_sai_da_mesa(entrada, config, bambu):
    executar = executor([-104, 0])

    ft.processar(entrada, config, bambu, executar=executar)

    assert len(executar.comandos) == 2


def test_recusa_definitiva_nao_repete(entrada, config, bambu):
    executar = executor([-51])

    with pytest.raises(ft.ErroFatiamento, match="código -51") as erro:
        ft.processar(entrada, config, bambu, executar=executar)

    assert erro.value.codigo == -51
    assert len(executar.comandos) == 1


def test_torre_sem_lugar_em_nenhuma_altura(entrada, config, bambu):
    with pytest.raises(ft.ErroFatiamento, match="torre de purga"):
        ft.processar(entrada, config, bambu, executar=executor([-101, -101, -101]))


def test_filamento_sem_gramas_e_erro(entrada, config, bambu):
    with pytest.raises(ft.ErroFatiamento, match="filamentos usados"):
        ft.processar(entrada, config, bambu, executar=executor(g2="0"))


def test_dimensao_divergente_e_erro(entrada, config, bambu):
    with pytest.raises(ft.ErroFatiamento, match="Dimensões"):
        ft.processar(entrada, config, bambu, executar=executor(largura=3.0))


def test_camada_divergente_e_erro():
    resumo = bambu_3mf.Resumo3mf(fatiado=True, camada_mm=0.2)

    with pytest.raises(ft.ErroFatiamento, match="Camada"):
        ft.conferir(resumo, None, [1, 1, 1], 0.12, [])


def test_sem_result_json(tmp_path):
    def executar(comando, **_):
        return subprocess.CompletedProcess(comando, 3221225477)

    with pytest.raises(ft.ErroFatiamento, match="não gerou result.json"):
        ft.fatiar("b.exe", tmp_path / "p.3mf", tmp_path, executar=executar)


def test_tempo_limite(tmp_path):
    def executar(comando, **_):
        raise subprocess.TimeoutExpired(comando, 1)

    with pytest.raises(ft.ErroFatiamento, match="tempo limite"):
        ft.fatiar("b.exe", tmp_path / "p.3mf", tmp_path, executar=executar)


def test_exe_que_nao_executa(tmp_path):
    def executar(comando, **_):
        raise OSError("sem acesso")

    with pytest.raises(ft.ErroFatiamento, match="Não foi possível executar"):
        ft.fatiar("b.exe", tmp_path / "p.3mf", tmp_path, executar=executar)


def test_aviso_de_timelapse_e_ignorado_e_outro_nao(entrada, config, bambu):
    avisos = ('<warning msg="not_support_traditional_timelapse" level="2"/>'
              '<warning msg="outro_aviso" level="1"/>')

    r = ft.processar(entrada, config, bambu, executar=executor(warning=avisos))

    assert r["avisos"] == ["outro_aviso"]


def test_avisa_versao_nao_testada(entrada, config, bambu):
    bambu["versao"] = "03.00.00.00"

    r = ft.processar(entrada, config, bambu, executar=executor())

    assert any("03.00.00.00" in a for a in r["avisos"])


def test_main_sem_bambu_studio(entrada, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GENERATE_BAMBU_CONFIG", str(tmp_path / "c.json"))
    monkeypatch.setattr(ft.diagnostico, "achar_bambu_studio",
                        lambda _: {"exe": None, "versao": None, "origem": None})

    assert ft.main([str(entrada)]) == 4
    assert "não encontrado" in capsys.readouterr().out


def test_main_entrada_invalida(tmp_path, monkeypatch, bambu):
    monkeypatch.setenv("GENERATE_BAMBU_CONFIG", str(tmp_path / "c.json"))
    monkeypatch.setattr(ft.diagnostico, "achar_bambu_studio", lambda _: bambu)

    assert ft.main([str(tmp_path / "nao-existe.3mf")]) == 2


def test_config_projeto_tem_um_valor_por_filamento(perfis_bbl, config):
    c = perfis.config_projeto(perfis_bbl, config["bambu_studio"], ["#111111", "#222222"],
                              "02.08.03.66", 160.0)

    assert c["filament_map"] == ["1", "1"]
    assert c["filament_self_index"] == ["1", "2"]
    assert c["filament_ids"] == ["GFA00", "GFA00"]
    assert c["nozzle_temperature"] == ["220", "220"]
    assert c["filament_colour"] == ["#111111", "#222222"]
    assert c["layer_height"] == "0.12"
    assert c["initial_layer_print_height"] == "0.24"
    assert c["printable_height"] == "250"
    assert c["machine_start_gcode"] == "G28"
    assert c["print_compatible_printers"] == ["A1"]
    assert c["wipe_tower_y"] == ["160.0", "160.0"]
    assert "inherits" not in c and "include" not in c and "type" not in c


def test_perfil_inexistente(perfis_bbl):
    with pytest.raises(perfis.ErroPerfil, match="não encontrado"):
        perfis.resolver(perfis_bbl, "process", "Nada")


@pytest.mark.parametrize(
    "largura, profundidade, n, y_torre, esperado",
    [
        (60, 30, 3, 207.957, (98, 113)),       # pequena: centrada
        (40, 40, 1, 207.957, (108, 108)),      # uma cor: sem torre
        (246, 123, 3, 207.957, (5, 66.5)),     # larga e rasa: passa embaixo da torre
        (170, 170, 2, 207.957, (43, 32.957)),  # desce: é o menor deslocamento
        (190, 190, 2, 207.957, (33, 12.957)),
        (150, 240, 2, 207.957, (60, 8)),       # alta demais para descer: anda em X
    ],
)
def test_posicionar(largura, profundidade, n, y_torre, esperado):
    assert pb.posicionar(largura, profundidade, n, y_torre) == pytest.approx(esperado)


def test_posicionar_sem_lugar_para_a_torre():
    assert pb.posicionar(200, 200, 2, 207.957) is None


def test_uma_cor_ocupa_a_mesa_toda():
    assert pb.posicionar(250, 250, 1, 207.957) == (3, 3)


def test_projeto_tem_uma_parte_por_slot(tmp_path):
    slots = [_slot("slot1", None), _slot("slot3", None, 20)]
    arquivo = tmp_path / "p.3mf"

    pb.gravar_projeto(slots, arquivo, {"layer_height": "0.12"}, 'peça "x"', "02.08.03.66", (10, 20))

    with zipfile.ZipFile(arquivo) as z:
        raiz = z.read("3D/3dmodel.model").decode()
        ajustes = z.read("Metadata/model_settings.config").decode()
        objetos = z.read("3D/Objects/object_1.model").decode()
    assert "BambuStudio-02.08.03.66" in raiz
    assert raiz.count("<component ") == 2
    assert "25.000000 25.000000 0" in raiz or "25.000000 25.000000" in raiz
    assert ajustes.count("<part ") == 2
    assert '<metadata key="extruder" value="2"/>' in ajustes
    assert 'value="slot3"' in ajustes
    assert objetos.count("<object ") == 2


def test_projeto_leva_a_base_para_z_zero(tmp_path):
    slots = [{"slot": "slot1", "cor": None, "tris": TRIS, "corpos": ["a"],
              "verts": [(x, y, z + 5) for x, y, z in CUBO]}]
    arquivo = tmp_path / "p.3mf"

    pb.gravar_projeto(slots, arquivo, {}, "p", "1", (0, 0))

    with zipfile.ZipFile(arquivo) as z:
        assert 'z="0.000000"' in z.read("3D/Objects/object_1.model").decode()


def test_ler_3mf_recusa_entidades(tmp_path):
    arquivo = tmp_path / "a.3mf"
    with zipfile.ZipFile(arquivo, "w") as z:
        z.writestr(bambu_3mf.SLICE_INFO, '<!DOCTYPE x [<!ENTITY a "b">]><config/>')

    with pytest.raises(bambu_3mf.Erro3mf, match="DTD"):
        bambu_3mf.ler_3mf(arquivo)


def test_ler_3mf_sem_fatiar(tmp_path):
    arquivo = tmp_path / "a.3mf"
    with zipfile.ZipFile(arquivo, "w") as z:
        z.writestr(bambu_3mf.SLICE_INFO, "<config><header/></config>")

    assert bambu_3mf.ler_3mf(arquivo).fatiado is False


def test_ler_3mf_corrompido(tmp_path):
    arquivo = tmp_path / "a.3mf"
    arquivo.write_bytes(b"nada")

    with pytest.raises(bambu_3mf.Erro3mf):
        bambu_3mf.ler_3mf(arquivo)


@pytest.mark.parametrize("valor, esperado", [("#e8b647", "#E8B647"), ("E8B647FF", "#E8B647")])
def test_normalizar_hex(valor, esperado):
    assert bambu_3mf.normalizar_hex(valor) == esperado
