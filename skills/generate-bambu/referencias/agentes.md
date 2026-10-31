# Agentes — capacidades, instalação e MCP

O `SKILL.md` descreve o que fazer, não qual ferramenta chamar. Esta tabela
traduz. Se a sua ferramenta tiver outro nome, vale a função, não o nome.

Os `fusion_mcp_*` são iguais em todo agente, porque vêm do próprio Fusion. O
agente pode exibi-los com prefixo do servidor, mas o final do nome é o mesmo.

> **Antes de usar:** a pasta `D:/Bambu Lab/projeto/`, o projeto "Bubble Studio
> 3D" e as notas de catálogo do `SKILL.md` são padrões do autor. Quem instalar
> precisa trocar pelos seus. Se a pasta de saída não existir, pergunte qual
> usar.

---

## Capacidades

| Capacidade | Claude | Codex | Gemini CLI e Antigravity |
|---|---|---|---|
| abrir programa | computer use: `open_application` | plugin Computer Use, se ativo | manual |
| esperar | `wait` | plugin Computer Use, se ativo | manual |
| capturar tela | `screenshot` | plugin Computer Use, se ativo | manual |
| clicar | `left_click` | plugin Computer Use, se ativo | manual |
| enviar atalho | `key` | plugin Computer Use, se ativo | manual |
| digitar | `type` | plugin Computer Use, se ativo | manual |
| focar ou maximizar janela | atalho de teclado ou clique | plugin Computer Use, se ativo | manual |
| ler nota | servidor MCP do Obsidian, se configurado (`obsidian_get_file_contents`) | idem | idem |
| inserir em nota | servidor MCP do Obsidian, se configurado (`obsidian_patch_content`) | idem | idem |

No Claude, as ferramentas de tela aparecem com prefixo (`mcp__computer-use__`
no Claude Code) e exigem pedir acesso ao programa antes, com `request_access`.

**Manual** quer dizer: siga "Sem controle de tela" no `SKILL.md`. Não tente
contornar com scripts que simulam clique.

---

## Como a skill chega a cada agente

Use **um canal só por agente**. Plugin e cópia da pasta juntos criam skills
duplicadas, e no Gemini a cópia vence a extensão e esconde atualizações.

| Agente | Canal recomendado | Pasta, sem plugin |
|---|---|---|
| Claude | plugin `generate-bambu@grolla05-plugins` | `~/.claude/skills/` |
| Codex | plugin `generate-bambu@grolla05-plugins` | `~/.agents/skills/` |
| Gemini CLI | `gemini extensions install` | `~/.gemini/skills/` |
| Antigravity | `agy plugin install` | `~/.gemini/config/skills/` |
| Antigravity CLI | `agy plugin install` | `~/.gemini/antigravity-cli/skills/` |

O `instalar.ps1` da raiz do repositório aplica esta tabela.

---

## MCP do Fusion

Servidor local em `http://127.0.0.1:27182/mcp`, com transporte Streamable HTTP
e sem autenticação. Só existe com o Fusion aberto e com Preferences → General
→ API → Fusion MCP Server ligado (*Apply* e depois *OK*).

| Agente | Onde | Como |
|---|---|---|
| Claude | extensão Autodesk Fusion do app, ou `claude mcp add` | `claude mcp add --transport http --scope user fusion http://127.0.0.1:27182/mcp` |
| Codex | plugin, ou `~/.codex/config.toml` | `[mcp_servers.fusion]` com `url` |
| Gemini CLI | extensão, ou `~/.gemini/settings.json` | `mcpServers.fusion.httpUrl` |
| Antigravity | plugin, ou `~/.gemini/config/mcp_config.json` | `mcpServers.fusion.serverUrl` |

Cuidado com a chave: no Gemini, `url` significa SSE e não funciona aqui; no
Antigravity, `httpUrl` não existe.

O plugin do Claude não traz esse servidor de propósito: duplicaria a extensão
do app e daria erro de conexão com o Fusion fechado.
