"""Testes do helper agrupar_3mf.py com 3MFs sintéticos no formato do Fusion."""

import xml.etree.ElementTree as ET
import zipfile

import pytest

from agrupar_3mf import NS_CORE, NS_MAT, agrupar_por_slot, ler_slots_fusion, montar_3mf

# Cubo unitário: 8 vértices e 12 triângulos, malha fechada e orientada para fora.
_VERTICES = [
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
]
_TRIANGULOS = [
    (0, 2, 1), (0, 3, 2),  # base
    (4, 5, 6), (4, 6, 7),  # topo
    (0, 1, 5), (0, 5, 4),  # frente
    (3, 7, 6), (3, 6, 2),  # fundo
    (0, 4, 7), (0, 7, 3),  # esquerda
    (1, 2, 6), (1, 6, 5),  # direita
]

VERMELHO = "#FF0000FF"
BRANCO = "#FFFFFFFF"


def _corpo(id_, nome, cor_idx, lado, x0=0.0, triangulos=None):
    """XML de um <object> do Fusion: um cubo de aresta `lado` em x0."""
    vs = "".join(
        f'<vertex x="{x * lado + x0}" y="{y * lado}" z="{z * lado}"/>'
        for x, y, z in _VERTICES
    )
    ts = "".join(
        f'<triangle v1="{a}" v2="{b}" v3="{c}"/>'
        for a, b, c in (triangulos if triangulos is not None else _TRIANGULOS)
    )
    return (
        f'<object id="{id_}" name="{nome}" type="model" pid="10" pindex="{cor_idx}">'
        f"<mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object>"
    )


def _escrever_3mf(caminho, corpos, itens="", unidade="millimeter",
                  cores=(VERMELHO, BRANCO)):
    bases = "".join(f'<base name="c{i}" displaycolor="{c}"/>' for i, c in enumerate(cores))
    modelo = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<model unit="{unidade}" xmlns="{NS_CORE}">'
        f'<resources><basematerials id="10">{bases}</basematerials>'
        f'{"".join(corpos)}</resources><build>{itens}</build></model>'
    )
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("3D/3dmodel.model", modelo)
    return caminho


def _ler_modelo(caminho):
    with zipfile.ZipFile(caminho) as z:
        return ET.fromstring(z.read("3D/3dmodel.model")), z.namelist()


@pytest.fixture
def entrada(tmp_path):
    """Base (slot1, 10 mm) e duas letras (slot2, 2 mm) — como o texto do Fusion."""
    return _escrever_3mf(tmp_path / "bruto.3mf", [
        _corpo(1, "slot1_base", 0, 10),
        _corpo(2, "slot2_texto_A", 1, 2),
        _corpo(3, "slot2_texto_B", 1, 2, x0=3),
    ])


def test_agrupa_corpos_do_mesmo_slot(entrada, tmp_path):
    rel = agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))

    assert [o["slot"] for o in rel["objetos"]] == ["slot1", "slot2"]
    assert [o["corpos"] for o in rel["objetos"]] == [1, 2]
    assert [o["triangulos"] for o in rel["objetos"]] == [12, 24]
    assert [o["cor"] for o in rel["objetos"]] == [VERMELHO, BRANCO]
    assert rel["unidade"] == "millimeter"
    assert rel["avisos"] == []


def test_volume_bate_com_a_geometria(entrada, tmp_path):
    rel = agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))

    volumes = {o["slot"]: o["volume_mm3"] for o in rel["objetos"]}
    assert volumes["slot1"] == pytest.approx(10 ** 3)
    assert volumes["slot2"] == pytest.approx(2 * 2 ** 3)


def test_malhas_fechadas(entrada, tmp_path):
    rel = agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))

    assert rel["tudo_fechado"] is True
    assert all(o["fechada"] for o in rel["objetos"])


def test_arquivo_de_saida_e_um_3mf_valido(entrada, tmp_path):
    final = tmp_path / "final.3mf"
    agrupar_por_slot(str(entrada), str(final))

    raiz, nomes = _ler_modelo(final)
    assert {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"} <= set(nomes)

    objetos = raiz.findall(f".//{{{NS_CORE}}}object")
    assert [o.get("name") for o in objetos] == ["slot1", "slot2"]
    assert len(raiz.findall(f".//{{{NS_CORE}}}item")) == 2

    cores = [c.get("color") for c in raiz.iter(f"{{{NS_MAT}}}color")]
    assert cores == [VERMELHO, BRANCO]
    # cor por triângulo: é o que o Bambu Studio lê num 3MF de terceiros
    triangulos = list(raiz.iter(f"{{{NS_CORE}}}triangle"))
    assert len(triangulos) == 36
    assert all(t.get("pid") == "100" for t in triangulos)


def test_sem_saida_sobrescreve_a_entrada(entrada):
    rel = agrupar_por_slot(str(entrada))

    assert rel["arquivo"] == str(entrada)
    raiz, _ = _ler_modelo(entrada)
    assert len(raiz.findall(f".//{{{NS_CORE}}}object")) == 2


def test_aplica_transformacao_do_item(tmp_path):
    entrada = _escrever_3mf(
        tmp_path / "bruto.3mf",
        [_corpo(1, "slot1_base", 0, 1)],
        itens='<item objectid="1" transform="1 0 0 0 1 0 0 0 1 5 0 0"/>',
    )
    final = tmp_path / "final.3mf"
    agrupar_por_slot(str(entrada), str(final))

    raiz, _ = _ler_modelo(final)
    xs = [float(v.get("x")) for v in raiz.iter(f"{{{NS_CORE}}}vertex")]
    assert min(xs) == pytest.approx(5.0)
    assert max(xs) == pytest.approx(6.0)


def test_slot_e_ordenado_numericamente(tmp_path):
    corpos = [_corpo(i, f"slot{n}_peca", 0, 1) for i, n in enumerate((3, 1, 2), start=1)]
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", corpos)

    rel = agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))

    assert [o["slot"] for o in rel["objetos"]] == ["slot1", "slot2", "slot3"]


def test_recusa_corpo_sem_prefixo_slot(tmp_path):
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", [
        _corpo(1, "slot1_base", 0, 1),
        _corpo(2, "Body3", 0, 1),
    ])

    with pytest.raises(ValueError, match="sem prefixo slotN_"):
        agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))


def test_recusa_mais_de_quatro_slots(tmp_path):
    corpos = [_corpo(n, f"slot{n}_peca", 0, 1) for n in range(1, 6)]
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", corpos)

    with pytest.raises(ValueError, match="a impressora tem 4"):
        agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))


def test_limite_de_slots_vem_da_impressora(tmp_path):
    corpos = [_corpo(n, f"slot{n}_peca", 0, 1) for n in (1, 2, 3)]
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", corpos)

    with pytest.raises(ValueError, match="fora de 1 a 2"):
        agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"), max_slots=2)


def test_recusa_unidade_que_nao_e_milimetro(tmp_path):
    entrada = _escrever_3mf(
        tmp_path / "bruto.3mf", [_corpo(1, "slot1_base", 0, 1)], unidade="inch"
    )

    with pytest.raises(ValueError, match="unidade"):
        agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))


def test_recusa_arquivo_sem_malha(tmp_path):
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", [])

    with pytest.raises(ValueError, match="nenhum objeto com malha"):
        agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))


def test_avisa_malha_aberta(tmp_path):
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", [
        _corpo(1, "slot1_base", 0, 1, triangulos=_TRIANGULOS[:-1]),
    ])

    rel = agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))

    assert rel["tudo_fechado"] is False
    assert rel["objetos"][0]["fechada"] is False
    assert any("malha não fechada" in a for a in rel["avisos"])


def test_avisa_cinza_padrao_do_fusion(tmp_path):
    entrada = _escrever_3mf(
        tmp_path / "bruto.3mf",
        [_corpo(1, "slot1_base", 0, 1)],
        cores=("#A0A0A0FF",),
    )

    rel = agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))

    assert any("cinza padrão" in a for a in rel["avisos"])


def test_recusa_cores_diferentes_no_mesmo_slot(tmp_path):
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", [
        _corpo(1, "slot1_a", 0, 1),
        _corpo(2, "slot1_b", 1, 1, x0=3),
    ])

    with pytest.raises(ValueError, match="cores diferentes"):
        agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))


@pytest.mark.parametrize("nome", ["slot0_x", "slot5_base"])
def test_recusa_slot_fora_de_um_a_quatro(tmp_path, nome):
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", [_corpo(1, nome, 0, 1)])

    with pytest.raises(ValueError, match="fora de 1 a 4"):
        agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))


@pytest.mark.parametrize(
    "nome", ["slot10abc", "slot1", "base_slot1", "SLOT1_x", "slot01_x", "slot1_"]
)
def test_recusa_nome_sem_contrato(tmp_path, nome):
    entrada = _escrever_3mf(tmp_path / "bruto.3mf", [_corpo(1, nome, 0, 1)])

    with pytest.raises(ValueError, match="sem prefixo"):
        agrupar_por_slot(str(entrada), str(tmp_path / "final.3mf"))


def test_arquivo_cru_nao_passa_como_agrupado(entrada):
    with pytest.raises(ValueError, match="não saiu do passo 3"):
        ler_slots_fusion(str(entrada), agrupado=True)


def test_arquivo_agrupado_passa_como_agrupado(entrada, tmp_path):
    final = tmp_path / "final.3mf"
    agrupar_por_slot(str(entrada), str(final))

    slots, _ = ler_slots_fusion(str(final), agrupado=True)

    assert [s["slot"] for s in slots] == ["slot1", "slot2"]


def test_ler_slots_devolve_malha_agrupada(entrada):
    slots, avisos = ler_slots_fusion(str(entrada))

    assert [s["slot"] for s in slots] == ["slot1", "slot2"]
    assert all(s["verts"] and s["tris"] and s["corpos"] for s in slots)
    assert avisos == []


def _slot(nome, cor=None):
    verts = [(float(x), float(y), float(z)) for x, y, z in _VERTICES]
    return {"slot": nome, "cor": cor, "verts": verts, "tris": _TRIANGULOS, "corpos": [nome]}


def test_montar_aceita_slots_de_outra_origem(tmp_path):
    rel = montar_3mf([_slot("slot2", "#123456FF")], str(tmp_path / "final.3mf"), avisos=["x"])

    assert rel["objetos"][0]["cor"] == "#123456FF"
    assert rel["tudo_fechado"]
    assert rel["avisos"] == ["x"]


def test_montar_avisa_slot_sem_cor(tmp_path):
    rel = montar_3mf([_slot("slot1")], str(tmp_path / "final.3mf"))

    assert any("cinza padrão" in a for a in rel["avisos"])


def test_montar_recusa_mais_de_quatro_slots(tmp_path):
    slots = [_slot(f"slot{i}") for i in range(1, 6)]

    with pytest.raises(ValueError, match="a impressora tem 4"):
        montar_3mf(slots, str(tmp_path / "final.3mf"))


def test_montar_respeita_limite_da_impressora(tmp_path):
    with pytest.raises(ValueError, match="a impressora tem 1"):
        montar_3mf([_slot("slot1"), _slot("slot2")], str(tmp_path / "final.3mf"), max_slots=1)
