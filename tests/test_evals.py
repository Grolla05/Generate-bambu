"""Os casos de avaliação entre agentes (evals/casos.yaml) seguem o formato combinado."""

import re

import pytest
import yaml
from conftest import RAIZ, SKILL

EVALS = RAIZ / "evals"
CAMPOS = {"id", "pedido", "deve", "nao_deve", "parada_esperada", "peso"}
OPCIONAIS = {"seguimento"}
PARADAS = {0, 2, 6}


@pytest.fixture(scope="module")
def casos():
    dados = yaml.safe_load((EVALS / "casos.yaml").read_text(encoding="utf-8"))
    assert isinstance(dados, dict) and isinstance(dados.get("casos"), list)
    return dados["casos"]


def test_yaml_tem_casos(casos):
    assert len(casos) >= 7
    assert all(isinstance(c, dict) for c in casos)


def test_ids_unicos_e_curtos(casos):
    ids = [c["id"] for c in casos]
    assert len(ids) == len(set(ids)), "ids repetidos em casos.yaml"
    for i in ids:
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", i), f"id fora do padrão: {i}"


def test_campos_obrigatorios(casos):
    for c in casos:
        faltando = CAMPOS - c.keys()
        assert not faltando, f"{c.get('id')}: faltam {sorted(faltando)}"
        extras = c.keys() - CAMPOS - OPCIONAIS
        assert not extras, f"{c['id']}: campos desconhecidos {sorted(extras)}"
        assert isinstance(c["pedido"], str) and c["pedido"].strip()
        for lista in ("deve", "nao_deve"):
            itens = c[lista]
            assert isinstance(itens, list) and itens, f"{c['id']}: {lista} vazio"
            assert all(isinstance(x, str) and x.strip() for x in itens)
        assert isinstance(c["peso"], int) and c["peso"] >= 1
        if "seguimento" in c:
            assert isinstance(c["seguimento"], list) and c["seguimento"]
            assert all(isinstance(x, str) and x.strip() for x in c["seguimento"])


def test_parada_esperada_e_um_passo_de_parada(casos):
    for c in casos:
        assert c["parada_esperada"] in PARADAS, c["id"]


def test_caso_imprimir_direto(casos):
    caso = next((c for c in casos if "imprimir direto" in c["pedido"].lower()), None)
    assert caso, "falta o caso em que o usuário pede para imprimir direto"
    assert caso["parada_esperada"] == 2
    proibido = " ".join(caso["nao_deve"]).lower()
    assert ".3mf" in proibido and "impressora" in proibido


def test_cobre_limites_da_triagem(casos):
    texto = " ".join(c["pedido"] for c in casos)
    assert "300 mm" in texto, "falta caso acima do limite de 250 mm"
    assert any(len(re.findall(r"vermelho|laranja|amarelo|verde|azul", c["pedido"])) >= 5
               for c in casos), "falta caso com mais de 4 cores"
    triagem = [c for c in casos if c["parada_esperada"] == 0]
    assert len(triagem) >= 4


def test_casos_a_e_b_nao_se_confundem(casos):
    por_id = {c["id"]: c for c in casos}
    a = " ".join(por_id["personagem-conhecido"]["nao_deve"]).lower()
    assert "estilizada" in a, "caso A precisa proibir versão estilizada do personagem"
    b = " ".join(por_id["rosto-realista"]["deve"]).lower()
    assert "estilizada" in b, "caso B precisa oferecer versão estilizada"


def test_rubrica_e_template_existem():
    rubrica = (EVALS / "rubrica.md").read_text(encoding="utf-8")
    for termo in ("Claude", "Codex", "Gemini CLI", "Antigravity", "Falha automática", ".3mf"):
        assert termo in rubrica
    template = (EVALS / "resultados" / "TEMPLATE.md").read_text(encoding="utf-8")
    for termo in ("Agente", "Versão", "Data", "Nota"):
        assert termo in template


def test_evals_fora_do_plugin():
    assert not (SKILL / "evals").exists()
    assert SKILL not in EVALS.parents
