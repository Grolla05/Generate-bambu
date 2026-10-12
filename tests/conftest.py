"""Configuração compartilhada dos testes.

O helper `agrupar_3mf.py` vive dentro do plugin (e é colado no script do Fusion),
então não é um pacote instalável: adicionamos a pasta dele ao sys.path.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLUGIN = RAIZ / "plugins" / "generate-bambu"
SKILL = PLUGIN / "skills" / "generate-bambu"

sys.path.insert(0, str(SKILL / "helpers"))
