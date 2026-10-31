"""Garante que os manifestos de cada agente contam a mesma história."""

import json
import re
import subprocess

from pathlib import Path

import pytest
import yaml
from conftest import RAIZ, SKILL, ler_frontmatter

NOME = "generate-bambu"
URL_FUSION = "http://127.0.0.1:27182/mcp"

MANIFESTOS = [
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".antigravity-plugin/plugin.json",
    "gemini-extension.json",
]
JSONS = MANIFESTOS + [
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    "mcp.json",
]
CAMPOS_DA_SKILL = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
CAMPOS_ANTIGRAVITY = {
    "$schema",
    "name",
    "displayName",
    "description",
    "version",
    "disabled",
    "logo",
    "suggestedPrompts",
    "skills",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
CAPACIDADES = [
    "rodar script",
    "abrir programa",
    "esperar",
    "capturar tela",
    "clicar",
    "enviar atalho",
    "digitar",
    "focar ou maximizar janela",
    "ler nota",
    "inserir em nota",
]
FORA_DO_REPOSITORIO = [
    "Bubble Studio",
    "catálogo religioso",
    "8 dos 11",
    "D:/Bambu Lab",
    "Empresa impressora 3D",
    "Risco Jurídico",
]
GATILHOS = ["chaveiro", "lembrancinha", "vaso", "keychain", "vase", "3MF", "Bambu"]


def _json(rel):
    return json.loads((RAIZ / rel).read_text(encoding="utf-8"))


def _skill_md():
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("rel", MANIFESTOS)
def test_manifesto_tem_nome_e_versao_da_skill(rel):
    manifesto = _json(rel)

    assert manifesto["name"] == NOME
    assert manifesto["version"] == ler_frontmatter()["metadata"]["version"]


def test_descricao_dos_manifestos_e_a_mesma():
    descricoes = {_json(rel)["description"] for rel in MANIFESTOS}
    descricoes.add(_json(".claude-plugin/marketplace.json")["plugins"][0]["description"])

    assert len(descricoes) == 1


@pytest.mark.parametrize("rel", JSONS)
def test_json_sem_bom(rel):
    assert not (RAIZ / rel).read_bytes().startswith(b"\xef\xbb\xbf")


def test_estrutura_nao_tem_o_que_foi_descartado():
    arquivos = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.splitlines()

    assert not [a for a in arquivos if a.startswith("plugins/")]
    # no Claude, `.mcp.json` carrega sozinho e duplicaria a extensão do Fusion
    assert ".mcp.json" not in arquivos
    # `.agents/skills` viraria skill de projeto ao abrir este repositório
    assert not [a for a in arquivos if a.startswith(".agents/skills/")]


def test_frontmatter_so_tem_campos_da_especificacao():
    campos = ler_frontmatter()

    assert set(campos) <= CAMPOS_DA_SKILL
    assert campos["name"] == SKILL.name
    assert len(campos["description"]) <= 1024
    assert len(campos["compatibility"]) <= 500
    assert all(isinstance(v, str) for v in campos["metadata"].values())


def test_descricao_tem_gatilhos_e_negativo():
    descricao = ler_frontmatter()["description"]

    assert [g for g in GATILHOS if g not in descricao] == []
    assert "SVG" in descricao


def test_manifesto_antigravity_respeita_o_schema():
    assert set(_json(".antigravity-plugin/plugin.json")) <= CAMPOS_ANTIGRAVITY


def test_marketplace_do_codex_bate_com_o_do_claude():
    codex = _json(".agents/plugins/marketplace.json")
    claude = _json(".claude-plugin/marketplace.json")

    # outro nome criaria um segundo ID de plugin em quem já instalou
    assert codex["name"] == claude["name"]
    entrada = codex["plugins"][0]
    assert entrada["name"] == NOME
    assert entrada["source"] == {"source": "local", "path": "./"}
    assert entrada["policy"]["installation"] == "AVAILABLE"
    assert entrada["policy"]["authentication"]
    assert entrada["category"]


def test_url_do_fusion_usa_a_chave_certa_de_cada_formato():
    portatil = _json("mcp.json")["mcpServers"]["fusion"]
    gemini = _json("gemini-extension.json")["mcpServers"]["fusion"]

    assert portatil == {"type": "streamable-http", "url": URL_FUSION}
    # no Gemini, `url` significa SSE
    assert gemini == {"httpUrl": URL_FUSION}
    assert _json(".codex-plugin/plugin.json")["mcpServers"] == "./mcp.json"


def test_openai_yaml_declara_o_fusion():
    config = yaml.safe_load((SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8"))

    assert config["policy"]["allow_implicit_invocation"] is True
    assert config["interface"]["display_name"]
    assert config["dependencies"]["tools"] == [
        {
            "type": "mcp",
            "value": "fusion",
            "description": "Servidor MCP local do Autodesk Fusion",
            "transport": "streamable_http",
            "url": URL_FUSION,
        }
    ]


@pytest.mark.parametrize("rel", JSONS)
def test_controle_de_tela_fica_fora_dos_manifestos(rel):
    assert "windows-mcp" not in (RAIZ / rel).read_text(encoding="utf-8").lower()


def test_mcp_do_blender_tambem_fica_fora_dos_manifestos():
    # executa código sem guarda: só entra por escolha de quem instala
    for rel in JSONS:
        assert "blender" not in json.dumps(_json(rel).get("mcpServers", {})).lower()


def test_skill_manda_o_usuario_clicar_em_imprimir():
    assert "Nenhum script desta skill envia peça para a" in _skill_md()
    arquivos = (SKILL / "scripts").glob("*.py")
    assert not [p.name for p in arquivos if p.name in ("imprimir.py", "enviar.py")]


def test_repositorio_publico_nao_carrega_o_negocio():
    arquivos = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout.splitlines()

    achados = {}
    for rel in arquivos:
        caminho = RAIZ / rel
        if rel == Path(__file__).relative_to(RAIZ).as_posix() or not caminho.is_file():
            continue
        texto = caminho.read_text(encoding="utf-8", errors="ignore")
        termos = [t for t in FORA_DO_REPOSITORIO if t in texto]
        if termos:
            achados[rel] = termos

    assert achados == {}


def test_prefixo_antigo_de_cor_so_existe_na_leitura():
    arquivos = subprocess.run(
        ["git", "grep", "-il", "bubble", "--", "skills", "README.md"],
        cwd=RAIZ, capture_output=True, text=True, check=False,
    ).stdout.split()

    assert set(arquivos) <= {
        "skills/generate-bambu/helpers/agrupar_3mf.py",
        "skills/generate-bambu/referencias/fusion-api.md",
    }


def test_versao_do_helper_bate_com_a_skill():
    from agrupar_3mf import APLICACAO

    assert APLICACAO == f"generate-bambu {ler_frontmatter()['metadata']['version']}"


def test_skill_nao_cita_ferramenta_de_um_agente_so():
    assert re.findall(r"computer_\w+|obsidian_\w+|mcp__\w+", _skill_md()) == []


def test_capacidades_estao_na_tabela_de_agentes():
    agentes = (SKILL / "referencias" / "agentes.md").read_text(encoding="utf-8")

    assert [c for c in CAPACIDADES if f"| {c} |" not in agentes] == []
