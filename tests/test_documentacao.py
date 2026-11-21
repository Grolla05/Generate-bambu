"""Garante que os trechos Python da documentação da skill ao menos compilam.

Os scripts de `fusion-api.md` usam a API do Fusion (`adsk`), que não existe fora
dele — então não dá para executá-los aqui, mas erro de sintaxe é pego.
"""

import ast
import re

import pytest
from conftest import SKILL, modulos_sem_import

_BLOCO = re.compile(r"```python[^\n]*\r?\n(.*?)```", re.DOTALL)


def _trechos():
    for md in sorted(SKILL.rglob("*.md")):
        texto = md.read_text(encoding="utf-8")
        for m in _BLOCO.finditer(texto):
            linha = texto.count("\n", 0, m.start()) + 1
            yield pytest.param(
                m.group(1), id=f"{md.relative_to(SKILL).as_posix()}:{linha}"
            )


def test_existem_trechos_python_na_documentacao():
    assert list(_trechos()), "nenhum bloco ```python encontrado — o regex quebrou?"


@pytest.mark.parametrize("codigo", list(_trechos()))
def test_trecho_python_compila(codigo):
    ast.parse(codigo)


def test_script_inteiro_importa_o_que_usa():
    scripts = [t.values[0] for t in _trechos() if "def run(context)" in t.values[0]]

    assert scripts, "nenhum script com run(context) — o filtro quebrou?"
    assert [s[:60] for s in scripts if modulos_sem_import(s)] == []


def test_detector_de_import_acusa_o_que_falta():
    assert modulos_sem_import("def run(context):\n    json.dumps({})\n") == ["json"]
