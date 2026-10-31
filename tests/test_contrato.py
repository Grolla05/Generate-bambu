"""O contrato de corpos vale igual no helper, na receita do Fusion e na do Blender."""

import contextlib
import io
import json
import re
import sys
import types
from types import SimpleNamespace as Obj

import agrupar_3mf as ag
import pytest
from conftest import SKILL

FUSION_API = (SKILL / "referencias" / "fusion-api.md").read_text(encoding="utf-8")
HELPER_BLENDER = (SKILL / "helpers" / "blender_3mf.py").read_text(encoding="utf-8")


def _literal(nome):
    m = re.search(rf"^{nome} = r'(.+)'$", FUSION_API, re.MULTILINE)
    assert m, f"{nome} sumiu de fusion-api.md"
    return m.group(1)


@pytest.mark.parametrize("nome", ["slot1_base", "slot4_texto_12", "slot2_a_b"])
def test_nome_dentro_do_contrato(nome):
    assert ag.RE_SLOT.match(nome)


@pytest.mark.parametrize(
    "nome", ["slot10abc", "slot1", "base_slot1", "SLOT1_x", "Slot1_x", "slot01_x", "slot1_"]
)
def test_nome_fora_do_contrato(nome):
    assert not ag.RE_SLOT.match(nome)


@pytest.mark.parametrize("nome", ["slot0_x", "slot5_base"])
def test_numero_fora_do_intervalo_e_lido_para_dar_erro_claro(nome):
    assert not 1 <= int(ag.RE_SLOT.match(nome).group(1)) <= ag.MAX_SLOTS


@pytest.mark.parametrize("nome", ["cor_#e8b647", "bubble_#e8b647"])
def test_prefixo_de_cor_novo_e_antigo(nome):
    assert ag.RE_COR.match(nome).group(1) == "#e8b647"


@pytest.mark.parametrize("nome", ["#e8b647", "cor_#E8B647", "cor_#e8b64", "Steel - Satin"])
def test_cor_fora_do_contrato(nome):
    assert not ag.RE_COR.match(nome)


def test_receita_do_fusion_usa_a_mesma_regex_do_helper():
    assert _literal("RE_SLOT") == ag.RE_SLOT.pattern
    assert _literal("RE_COR") == ag.RE_COR.pattern


def test_blender_importa_o_contrato_em_vez_de_repetir():
    assert "from agrupar_3mf import" in HELPER_BLENDER
    assert "re.compile" not in HELPER_BLENDER


def _ponto(x, y, z):
    return Obj(x=x, y=y, z=z)


def _corpo(nome, z0=0.0, z1=0.12, cor="cor_#112233", solido=True, x0=0.0):
    """Unidades da API: cm. Caixa de 1 × 1 cm."""
    return Obj(
        name=nome,
        isSolid=solido,
        volume=1.0,
        appearance=Obj(name=cor) if cor else None,
        boundingBox=Obj(minPoint=_ponto(x0, 0, z0), maxPoint=_ponto(x0 + 1, 1, z1)),
    )


class _Corpos(list):
    @property
    def count(self):
        return len(self)


def _validar(corpos, camada=0.012, extras=(), curva=False, interferencias=()):
    """Roda o bloco de validação de fusion-api.md com um `adsk` falso."""
    raiz = Obj(id="raiz", name="raiz", bRepBodies=_Corpos(corpos))
    outros = [Obj(id=f"c{i}", name=f"c{i}", bRepBodies=_Corpos([b])) for i, b in enumerate(extras)]
    parametro = Obj(value=camada) if camada else None
    design = Obj(
        rootComponent=raiz,
        allComponents=[raiz, *outros],
        userParameters=Obj(itemByName=lambda _: parametro),
        createInterferenceInput=lambda colecao: colecao,
        analyzeInterference=lambda _: list(interferencias),
    )
    adsk = types.ModuleType("adsk")
    adsk.core = types.ModuleType("adsk.core")
    adsk.fusion = types.ModuleType("adsk.fusion")
    adsk.core.Application = Obj(get=lambda: Obj(activeProduct=design))
    adsk.core.ObjectCollection = Obj(create=lambda: Obj(add=lambda _: None))
    adsk.fusion.Design = Obj(cast=lambda d: d)

    ini = FUSION_API.index("## Validação (passo 1c)")
    bloco = re.search(r"```python\r?\n(.*?)```", FUSION_API[ini:], re.DOTALL).group(1)
    if curva:
        bloco = bloco.replace("CURVA = False", "CURVA = True")
    modulos = {"adsk": adsk, "adsk.core": adsk.core, "adsk.fusion": adsk.fusion}
    saida = io.StringIO()
    espaco = {}
    antes = {k: sys.modules.get(k) for k in modulos}
    sys.modules.update(modulos)
    try:
        exec(bloco, espaco)
        with contextlib.redirect_stdout(saida):
            espaco["run"](None)
    finally:
        for chave, valor in antes.items():
            if valor is None:
                sys.modules.pop(chave, None)
            else:
                sys.modules[chave] = valor
    return json.loads(saida.getvalue())


def _tem_erro(resultado, trecho):
    return any(trecho in e for e in resultado["erros"])


def test_validacao_aprova_peca_boa():
    resultado = _validar([
        _corpo("slot1_base"),
        _corpo("slot2_texto_1", z0=0.12, z1=0.204, cor="cor_#ffffff", x0=2),
    ])

    assert resultado["ok"] is True
    assert resultado["erros"] == []
    assert resultado["n_slots"] == 2
    assert resultado["total_mm"] == [30.0, 10.0, 2.04]


@pytest.mark.parametrize("nome", ["Body1", "slot5_base", "slot0_x", "SLOT1_x", "slot1_"])
def test_validacao_recusa_nome_fora_do_contrato(nome):
    resultado = _validar([_corpo(nome)])

    assert resultado["ok"] is False
    assert _tem_erro(resultado, "fora do contrato")


def test_validacao_recusa_sem_parametro_camada():
    assert _tem_erro(_validar([_corpo("slot1_base")], camada=None), "camada ausente")


def test_validacao_recusa_duas_cores_no_slot():
    resultado = _validar([
        _corpo("slot1_a"),
        _corpo("slot1_b", cor="cor_#ffffff", x0=2),
    ])

    assert _tem_erro(resultado, "cores diferentes")


def test_validacao_recusa_corpo_em_subcomponente():
    resultado = _validar([_corpo("slot1_base")], extras=[_corpo("slot1_escondido")])

    assert _tem_erro(resultado, "subcomponente")


def test_validacao_recusa_cor_padrao_do_fusion():
    assert _tem_erro(_validar([_corpo("slot1_base", cor="Steel - Satin")]), "fora do padrão")


def test_validacao_aceita_prefixo_antigo():
    assert _validar([_corpo("slot1_base", cor="bubble_#112233")])["ok"] is True


def test_validacao_recusa_corpo_nao_solido():
    assert _tem_erro(_validar([_corpo("slot1_base", solido=False)]), "não sólido")


def test_validacao_recusa_peca_maior_que_o_limite():
    resultado = _validar([_corpo("slot1_a"), _corpo("slot1_b", x0=30)])

    assert _tem_erro(resultado, "não cabe")


def test_altura_fora_da_camada_e_erro_em_peca_plana():
    assert _tem_erro(_validar([_corpo("slot1_base", z1=0.1)]), "múltiplo da camada")


def test_altura_fora_da_camada_e_aviso_em_forma_curva():
    resultado = _validar([_corpo("slot1_vaso", z1=0.1)], curva=True)

    assert resultado["ok"] is True
    assert any("múltiplo da camada" in a for a in resultado["avisos"])


def test_validacao_recusa_volume_sobreposto():
    conflito = Obj(
        entityOne=Obj(name="slot1_a"),
        entityTwo=Obj(name="slot2_b"),
        interferenceBody=Obj(volume=0.5),
    )
    resultado = _validar(
        [_corpo("slot1_a"), _corpo("slot2_b", cor="cor_#ffffff")], interferencias=[conflito]
    )

    assert _tem_erro(resultado, "sobrepostos")


def test_validacao_recusa_design_vazio():
    assert _tem_erro(_validar([]), "sem corpos")
