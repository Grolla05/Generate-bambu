"""Esqueleto das peças-base de `modelos/`.

Os scripts usam a API do Fusion (`adsk`), então aqui só dá para conferir a forma:
compila, importa o que usa, segue o contrato de corpos e de camada, e está na
tabela do README da pasta. Rodar de verdade é no Fusion, antes do commit.
"""

import ast
import re

import agrupar_3mf as ag
import pytest
from conftest import SKILL, modulos_sem_import

MODELOS = SKILL / "modelos"
ARQUIVOS = sorted(MODELOS.glob("*.py"))
LEIA = (MODELOS / "README.md").read_text(encoding="utf-8")


def _codigo(arquivo):
    return arquivo.read_text(encoding="utf-8")


def _nomes_de_corpo(codigo):
    """Literais (ou f-strings, sem a parte variável) atribuídos a `<algo>.name`."""
    nomes = []
    for no in ast.walk(ast.parse(codigo)):
        if not isinstance(no, ast.Assign):
            continue
        alvo = no.targets[0]
        if not (isinstance(alvo, ast.Attribute) and alvo.attr == "name"):
            continue
        valor = no.value
        if isinstance(valor, ast.Constant):
            nomes.append(valor.value)
        elif isinstance(valor, ast.JoinedStr):
            nomes.append("".join(
                p.value if isinstance(p, ast.Constant) else "1" for p in valor.values))
    return nomes


def test_existem_modelos():
    assert len(ARQUIVOS) >= 5


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_modelo_compila_e_define_run(arquivo):
    arvore = ast.parse(_codigo(arquivo))
    funcoes = {no.name for no in arvore.body if isinstance(no, ast.FunctionDef)}
    assert "run" in funcoes
    assert ast.get_docstring(arvore), "docstring com slots e uso"


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_modelo_importa_o_que_usa(arquivo):
    assert modulos_sem_import(_codigo(arquivo)) == []


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_parametros_ficam_num_bloco_no_topo(arquivo):
    linhas = _codigo(arquivo).splitlines()
    marcas = [i for i, linha in enumerate(linhas) if linha.startswith("# ---")]
    assert len(marcas) == 2, "bloco de parâmetros entre duas linhas '# ---'"
    run = next(i for i, linha in enumerate(linhas) if linha.startswith("def run("))
    assert marcas[1] < run


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_corpos_seguem_o_contrato(arquivo):
    nomes = _nomes_de_corpo(_codigo(arquivo))
    assert nomes, "nenhum corpo nomeado"
    for nome in nomes:
        nome = nome.replace("{slot_texto}", "3")
        m = ag.RE_SLOT.match(nome)
        assert m and 1 <= int(m.group(1)) <= ag.MAX_SLOTS, nome


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_alturas_sao_multiplos_da_camada(arquivo):
    codigo = _codigo(arquivo)
    assert "up.add('camada', VI.createByString(f'{CAMADA} mm')" in codigo
    assert re.search(r"^CAMADA = 0\.12$", codigo, re.MULTILINE)
    for nome, expr in re.findall(r"up\.add\('(\w+)', VI\.createByString\(f?'([^']+)'\)", codigo):
        if nome in ("camada", "folga"):
            continue
        assert "* camada" in expr, f"{nome} = {expr}"


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_modelo_nao_exporta_nem_salva(arquivo):
    codigo = _codigo(arquivo)
    for proibido in ("exportManager", "saveAs", ".save(", "sendToPrintUtility"):
        assert proibido not in codigo


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_modelo_enquadra_a_vista(arquivo):
    assert "app.activeViewport.fit()" in _codigo(arquivo)


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_colorir_igual_ao_de_todos(arquivo):
    def corpo(arq):
        texto = _codigo(arq)
        i = texto.index("    def colorir(")
        return texto[i:texto.index("body.appearance = a", i)]

    assert corpo(arquivo) == corpo(ARQUIVOS[0])


def test_readme_lista_exatamente_os_modelos():
    citados = set(re.findall(r"^\| `(\w+\.py)` \|", LEIA, re.MULTILINE))
    assert citados == {a.name for a in ARQUIVOS}
