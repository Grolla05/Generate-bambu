"""Configuração compartilhada dos testes.

O helper `agrupar_3mf.py` vive dentro do plugin (e é colado no script do Fusion) e
os scripts rodam soltos, sem pacote: adicionamos as duas pastas ao sys.path.
"""

import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
PLUGIN = RAIZ
SKILL = RAIZ / "skills" / "generate-bambu"

sys.path.insert(0, str(SKILL / "helpers"))
sys.path.insert(0, str(SKILL / "scripts"))


def ler_frontmatter():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"---\r?\n(.*?)\r?\n---", texto, re.DOTALL)
    assert m, "SKILL.md precisa começar com frontmatter YAML"
    return yaml.safe_load(m.group(1))
