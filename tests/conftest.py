"""Configuração compartilhada dos testes.

O helper `agrupar_3mf.py` vive dentro do plugin (e é colado no script do Fusion),
então não é um pacote instalável: adicionamos a pasta dele ao sys.path.
"""

import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
PLUGIN = RAIZ / "plugins" / "generate-bambu"
SKILL = PLUGIN / "skills" / "generate-bambu"

sys.path.insert(0, str(SKILL / "helpers"))


def ler_frontmatter():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"---\r?\n(.*?)\r?\n---", texto, re.DOTALL)
    assert m, "SKILL.md precisa começar com frontmatter YAML"
    return yaml.safe_load(m.group(1))
