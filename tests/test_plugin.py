"""Valida os manifestos do plugin e a consistência com a skill."""

import json
import re

from conftest import PLUGIN, RAIZ, SKILL, ler_frontmatter


def _json(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


def test_plugin_json_tem_os_campos_obrigatorios():
    plugin = _json(PLUGIN / ".claude-plugin" / "plugin.json")

    assert plugin["name"] == "generate-bambu"
    assert re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])
    assert plugin["description"]


def test_marketplace_aponta_para_o_plugin():
    marketplace = _json(RAIZ / ".claude-plugin" / "marketplace.json")
    plugin = _json(PLUGIN / ".claude-plugin" / "plugin.json")

    assert marketplace["name"] and marketplace["owner"]["name"]
    assert len(marketplace["plugins"]) == 1
    entrada = marketplace["plugins"][0]
    # nome da entrada e nome do manifesto precisam ser iguais, senão o install falha
    assert entrada["name"] == plugin["name"]
    assert (RAIZ / entrada["source"] / ".claude-plugin" / "plugin.json").is_file()


def test_skill_tem_frontmatter_valido():
    campos = ler_frontmatter()

    assert campos["name"] == "generate-bambu"
    assert isinstance(campos["description"], str) and campos["description"].strip()


def test_arquivos_citados_na_skill_existem():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    citados = set(re.findall(r"`((?:referencias|helpers)/[\w./-]+)`", texto))

    assert citados, "o SKILL.md deveria citar referencias/ e helpers/"
    for rel in citados:
        assert (SKILL / rel).is_file(), f"{rel} citado no SKILL.md, mas não existe"
