"""Testa o instalar.ps1 contra uma pasta de usuário falsa.

Só roda no Windows: o script é para PowerShell 5.1. Nenhum teste toca na
configuração real, e os valores de `SEGREDO` provam que nada vaza na saída.
"""

import json
import os
import shutil
import subprocess

import pytest
from conftest import RAIZ, SKILL

SCRIPT = RAIZ / "instalar.ps1"
NOME = SKILL.name
URL = "http://127.0.0.1:27182/mcp"
SEGREDO = "fixture-segredo-nao-pode-vazar"
BOM = b"\xef\xbb\xbf"

windows = pytest.mark.skipif(
    shutil.which("powershell.exe") is None, reason="exige PowerShell do Windows"
)


def rodar(home, *argumentos, binarios="", env=None):
    comando = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT),
        "-RaizHome",
        str(home),
        "-BinariosTeste",
        binarios,
        *argumentos,
    ]
    return subprocess.run(
        comando, capture_output=True, text=True, encoding="oem", errors="replace", env=env
    )


def instalar(home, *argumentos, **opcoes):
    resultado = rodar(home, "-Sim", *argumentos, **opcoes)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    return resultado


def gravar(caminho, texto, bom=False):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = texto.encode("utf-8")
    caminho.write_bytes(BOM + dados if bom else dados)
    return caminho


def foto(home):
    return {
        p.relative_to(home).as_posix(): p.read_bytes() for p in home.rglob("*") if p.is_file()
    }


def backups(arquivo):
    return list(arquivo.parent.glob(arquivo.name + ".bak-*"))


@pytest.fixture
def home(tmp_path):
    pasta = tmp_path / "Usuário com espaço"
    pasta.mkdir()
    return pasta


def test_script_e_seguro_para_o_powershell_5():
    dados = SCRIPT.read_bytes()

    # sem BOM, o 5.1 lê UTF-8 como ANSI e corrompe os acentos
    assert dados.startswith(BOM) or dados.isascii()
    assert b"\r\n" in dados and b"\n" not in dados.replace(b"\r\n", b"")


@windows
def test_simular_nao_grava_nada(home):
    gravar(home / ".codex" / "config.toml", "model = 'x'\n")
    gravar(home / ".gemini" / "config" / "mcp_config.json", '{"mcpServers": {}}')
    antes = foto(home)

    resultado = rodar(home, "-Simular", binarios="gemini,claude")

    assert resultado.returncode == 0, resultado.stdout
    assert "[copiar]" in resultado.stdout
    assert foto(home) == antes


@windows
def test_pede_confirmacao_sem_sim(home):
    gravar(home / ".codex" / "config.toml", "")

    resultado = rodar(home)

    assert resultado.returncode != 0
    assert not (home / ".agents" / "skills" / NOME).exists()


@windows
def test_nao_detecta_gemini_so_pela_pasta(home):
    (home / ".gemini").mkdir()

    instalar(home)

    assert not (home / ".gemini" / "skills").exists()
    assert not (home / ".gemini" / "settings.json").exists()


@windows
def test_agentes_restringe_o_alvo(home):
    (home / ".claude").mkdir()
    gravar(home / ".codex" / "config.toml", "")

    instalar(home, "-Agentes", "claude")

    assert (home / ".claude" / "skills" / NOME / "SKILL.md").is_file()
    assert (home / ".codex" / "config.toml").read_text() == ""


@windows
def test_agente_desconhecido_falha(home):
    assert rodar(home, "-Agentes", "cursor").returncode != 0


@windows
def test_copia_a_skill_sem_lixo_e_com_marcador(home):
    (home / ".claude").mkdir()
    lixo = SKILL / "helpers" / "__pycache__"
    lixo.mkdir(exist_ok=True)

    instalar(home)

    destino = home / ".claude" / "skills" / NOME
    assert (destino / "referencias" / "agentes.md").is_file()
    assert (destino / "agents" / "openai.yaml").is_file()
    assert (destino / ".instalado-por-generate-bambu").is_file()
    assert not (destino / "helpers" / "__pycache__").exists()


@windows
def test_rodar_duas_vezes_e_idempotente(home):
    (home / ".claude").mkdir()
    config = gravar(home / ".codex" / "config.toml", "model = 'x'\n")
    gravar(home / ".gemini" / "config" / "mcp_config.json", '{"mcpServers": {}}')

    instalar(home, binarios="gemini,agy")
    depois = foto(home)
    instalar(home, binarios="gemini,agy")

    assert foto(home) == depois
    assert (home / ".claude" / "skills" / NOME / "SKILL.md").is_file()
    assert not (home / ".claude" / "skills" / NOME / NOME).exists()
    assert config.read_text().count("[mcp_servers.fusion]") == 1


@pytest.mark.parametrize(
    ("relativo", "chave", "binarios"),
    [
        (".gemini/settings.json", "httpUrl", "gemini"),
        (".gemini/config/mcp_config.json", "serverUrl", ""),
    ],
)
@windows
def test_json_preserva_o_resto_do_arquivo(home, relativo, chave, binarios):
    original = {
        "$typeName": "tipo",
        "tema": "Ação",
        "mcpServers": {
            "obsidian": {
                "command": "uvx",
                "args": ["um-so"],
                "env": {"TOKEN": SEGREDO, "a": {"b": {"c": {"d": [1, {"e": "f"}]}}}},
            }
        },
    }
    arquivo = gravar(home / relativo, json.dumps(original, ensure_ascii=False, indent=2))
    (home / ".gemini" / "config").mkdir(exist_ok=True)

    resultado = instalar(home, "-Agentes", "gemini,antigravity", binarios=binarios)

    dados = arquivo.read_bytes()
    assert not dados.startswith(BOM)
    novo = json.loads(dados)
    assert novo["mcpServers"].pop("fusion") == {chave: URL}
    assert novo == original
    assert SEGREDO not in resultado.stdout
    assert len(backups(arquivo)) == 1


@windows
def test_json_sem_mcp_servers_ganha_a_chave(home):
    arquivo = gravar(home / ".gemini" / "settings.json", '{\r\n  "tema": "x"\r\n}\r\n')

    instalar(home, binarios="gemini")

    dados = json.loads(arquivo.read_bytes())
    assert dados["tema"] == "x"
    assert dados["mcpServers"]["fusion"] == {"httpUrl": URL}


@windows
def test_json_com_bom_e_lido_e_sai_sem_bom(home):
    arquivo = gravar(home / ".gemini" / "settings.json", '{"mcpServers": {}}', bom=True)

    instalar(home, binarios="gemini")

    assert not arquivo.read_bytes().startswith(BOM)
    assert json.loads(arquivo.read_bytes())["mcpServers"]["fusion"] == {"httpUrl": URL}


@pytest.mark.parametrize(
    "conteudo",
    [
        '{\n  // comentário\n  "token": "%s"\n}' % SEGREDO,
        '{"token": "%s"' % SEGREDO,
        "",
        '["%s"]' % SEGREDO,
        '{"mcpServers": ["%s"]}' % SEGREDO,
    ],
    ids=["jsonc", "invalido", "vazio", "lista", "servidores-lista"],
)
@windows
def test_json_inesperado_aborta_com_original_intacto(home, conteudo):
    arquivo = gravar(home / ".gemini" / "settings.json", conteudo)

    resultado = rodar(home, "-Sim", binarios="gemini")

    assert resultado.returncode != 0
    assert arquivo.read_text(encoding="utf-8") == conteudo
    assert backups(arquivo) == []
    assert SEGREDO not in resultado.stdout + resultado.stderr


@windows
def test_json_com_fusion_diferente_e_preservado(home):
    conteudo = '{"mcpServers": {"fusion": {"httpUrl": "http://127.0.0.1:9/mcp"}}}'
    arquivo = gravar(home / ".gemini" / "settings.json", conteudo)

    resultado = instalar(home, binarios="gemini")

    assert arquivo.read_text() == conteudo
    assert "[aviso]" in resultado.stdout
    assert "127.0.0.1:9" not in resultado.stdout


@windows
def test_toml_sem_quebra_final_recebe_bloco_valido(home):
    tomllib = pytest.importorskip("tomllib")
    arquivo = gravar(home / ".codex" / "config.toml", 'model = "x"')

    instalar(home)

    dados = tomllib.loads(arquivo.read_text())
    assert dados["model"] == "x"
    assert dados["mcp_servers"]["fusion"] == {"url": URL}


@pytest.mark.parametrize(
    "conteudo",
    [
        '[mcp_servers.fusion]\nurl = "http://127.0.0.1:9/mcp"\n',
        'mcp_servers.fusion.url = "http://127.0.0.1:9/mcp"\n',
        'mcp_servers = { fusion = { url = "http://127.0.0.1:9/mcp" } }\n',
    ],
    ids=["tabela", "pontilhada", "inline"],
)
@windows
def test_toml_com_fusion_diferente_e_preservado(home, conteudo):
    arquivo = gravar(home / ".codex" / "config.toml", conteudo)

    resultado = instalar(home)

    assert arquivo.read_text() == conteudo
    assert "[aviso]" in resultado.stdout


@windows
def test_toml_com_fusion_igual_nao_duplica(home):
    conteudo = f'[mcp_servers.fusion]\nurl = "{URL}"\n'
    arquivo = gravar(home / ".codex" / "config.toml", conteudo)

    instalar(home)

    assert arquivo.read_text() == conteudo


@windows
def test_plugin_do_claude_presente_pula_a_copia(home):
    gravar(
        home / ".claude" / "plugins" / "installed_plugins.json",
        '{"plugins": {"generate-bambu@grolla05-plugins": []}}',
    )

    instalar(home)

    assert not (home / ".claude" / "skills").exists()


@windows
def test_plugin_do_codex_presente_pula_copia_e_mcp_e_avisa_duplicata(home):
    conteudo = (
        '[plugins."generate-bambu@grolla05-plugins"]\nenabled = true\n\n'
        '[plugins."generate-bambu@claude-cowork"]\nenabled = true\n'
    )
    arquivo = gravar(home / ".codex" / "config.toml", conteudo)

    resultado = instalar(home)

    assert arquivo.read_text() == conteudo
    assert not (home / ".agents").exists()
    assert "[aviso]" in resultado.stdout


@windows
def test_extensao_do_gemini_presente_nao_grava_nada(home):
    (home / ".gemini" / "extensions" / NOME).mkdir(parents=True)

    instalar(home, binarios="gemini")

    assert not (home / ".gemini" / "skills").exists()
    assert not (home / ".gemini" / "settings.json").exists()


@windows
def test_plugin_do_antigravity_presente_nao_grava_nada(home):
    (home / ".gemini" / "config" / "plugins" / NOME).mkdir(parents=True)

    instalar(home, binarios="agy")

    assert not (home / ".gemini" / "config" / "skills").exists()
    assert not (home / ".gemini" / "config" / "mcp_config.json").exists()


@windows
def test_pasta_compartilhada_evita_copia_para_gemini_e_antigravity(home):
    gravar(home / ".codex" / "config.toml", "")
    (home / ".gemini" / "config").mkdir(parents=True)

    instalar(home, binarios="gemini,agy")

    assert (home / ".agents" / "skills" / NOME / "SKILL.md").is_file()
    assert not (home / ".gemini" / "skills").exists()
    assert not (home / ".gemini" / "config" / "skills").exists()
    # o agy não lê ~/.agents/skills
    assert (home / ".gemini" / "antigravity-cli" / "skills" / NOME / "SKILL.md").is_file()


@windows
def test_antigravity_e_agy_gravam_o_mcp_uma_vez(home):
    arquivo = gravar(home / ".gemini" / "config" / "mcp_config.json", '{"mcpServers": {}}')

    instalar(home, binarios="agy")

    assert json.loads(arquivo.read_bytes()) == {"mcpServers": {"fusion": {"serverUrl": URL}}}


@windows
def test_pasta_alheia_e_mantida(home):
    manual = gravar(home / ".claude" / "skills" / NOME / "SKILL.md", "minha cópia")

    resultado = instalar(home)

    assert manual.read_text(encoding="utf-8") == "minha cópia"
    assert "[aviso]" in resultado.stdout


@windows
def test_destino_reparse_point_e_recusado(home, tmp_path):
    alvo = tmp_path / "fora"
    alvo.mkdir()
    (alvo / "vizinho.txt").write_text("fica")
    pasta = home / ".claude" / "skills"
    pasta.mkdir(parents=True)
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(pasta / NOME), str(alvo)],
        check=True,
        capture_output=True,
    )

    resultado = rodar(home, "-Sim")

    assert resultado.returncode != 0
    assert (alvo / "vizinho.txt").read_text() == "fica"
    assert not (alvo / "SKILL.md").exists()


@windows
def test_desinstalar_remove_so_o_que_e_nosso(home):
    (home / ".agents" / "skills" / "synced").mkdir(parents=True)
    (home / ".agents" / "skills" / ".trash").mkdir()
    config = gravar(home / ".codex" / "config.toml", "model = 'x'\n")
    gemini = gravar(home / ".gemini" / "settings.json", '{"mcpServers": {"outro": {"url": "u"}}}')
    antigravity = gravar(home / ".gemini" / "config" / "mcp_config.json", '{"mcpServers": {}}')

    instalar(home, binarios="gemini,agy")
    assert "fusion" in config.read_text()
    instalar(home, "-Desinstalar", binarios="gemini,agy")

    assert not (home / ".agents" / "skills" / NOME).exists()
    assert (home / ".agents" / "skills" / "synced").is_dir()
    assert (home / ".agents" / "skills" / ".trash").is_dir()
    assert config.read_text() == "model = 'x'\n"
    assert json.loads(gemini.read_bytes()) == {"mcpServers": {"outro": {"url": "u"}}}
    assert json.loads(antigravity.read_bytes()) == {"mcpServers": {}}


@windows
def test_desinstalar_mantem_entrada_alterada_e_pasta_alheia(home):
    manual = gravar(home / ".claude" / "skills" / NOME / "SKILL.md", "minha cópia")
    conteudo = '{"mcpServers": {"fusion": {"httpUrl": "http://127.0.0.1:9/mcp"}}}'
    gemini = gravar(home / ".gemini" / "settings.json", conteudo)

    instalar(home, "-Desinstalar")

    assert manual.is_file()
    assert gemini.read_text() == conteudo


@windows
def test_mcp_claude_so_com_a_opcao(home, tmp_path):
    bin_falso = tmp_path / "bin"
    registro = tmp_path / "chamadas.txt"
    gravar(bin_falso / "claude.cmd", f'@echo %* >> "{registro}"\n@exit /b 1\n')
    (home / ".claude").mkdir()
    env = {**os.environ, "PATH": f"{bin_falso}{os.pathsep}{os.environ['PATH']}"}

    instalar(home, binarios="claude", env=env)
    assert not registro.exists()

    resultado = rodar(home, "-Sim", "-McpClaude", binarios="claude", env=env)

    assert "mcp add --transport http --scope user fusion" in registro.read_text()
    # o `claude.cmd` falso sempre devolve erro
    assert resultado.returncode != 0
