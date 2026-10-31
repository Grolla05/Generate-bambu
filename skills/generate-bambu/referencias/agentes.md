# Agentes — capacidades, instalação e MCP

O `SKILL.md` descreve o que fazer, não qual ferramenta chamar. Esta tabela
traduz. Se a sua ferramenta tiver outro nome, vale a função, não o nome.

Os `fusion_mcp_*` são iguais em todo agente, porque vêm do próprio Fusion, e o
mesmo vale para as ferramentas do Blender. O agente pode exibi-las com prefixo do
servidor, mas o final do nome é o mesmo.

> **Configuração:** pasta de saída, Bambu Studio, máquina e projeto do Fusion ficam
> em `~/.generate-bambu/config.json` (modelo em `config.example.json`), e o contexto
> de quem usa fica em `~/.generate-bambu/perfil.md` (modelo em `perfil.example.md`).
> Os dois moram fora da skill porque atualizar o plugin troca a pasta dela.

---

## Capacidades

| Capacidade | Claude | Codex | Gemini CLI e Antigravity |
|---|---|---|---|
| rodar script | terminal | terminal | terminal |
| abrir programa | computer use: `open_application` | plugin Computer Use ou Windows-MCP: `App` | Windows-MCP: `App` |
| esperar | `wait` | plugin Computer Use ou Windows-MCP: `Wait` | Windows-MCP: `Wait` |
| capturar tela | `screenshot` | plugin Computer Use ou Windows-MCP: `Screenshot`, `Snapshot` | Windows-MCP: `Screenshot`, `Snapshot` |
| clicar | `left_click` | plugin Computer Use ou Windows-MCP: `Click` | Windows-MCP: `Click` |
| enviar atalho | `key` | plugin Computer Use ou Windows-MCP: `Shortcut` | Windows-MCP: `Shortcut` |
| digitar | `type` | plugin Computer Use ou Windows-MCP: `Type` | Windows-MCP: `Type` |
| focar ou maximizar janela | atalho de teclado ou clique | plugin Computer Use ou Windows-MCP: `App` | Windows-MCP: `App` |
| ler nota | servidor MCP do Obsidian, se configurado (`obsidian_get_file_contents`) | idem | idem |
| inserir em nota | servidor MCP do Obsidian, se configurado (`obsidian_patch_content`) | idem | idem |

No Claude, as ferramentas de tela aparecem com prefixo (`mcp__computer-use__`
no Claude Code) e exigem pedir acesso ao programa antes, com `request_access`.

Sem nenhuma dessas ferramentas, siga "Roteiro para o usuário" em
`bambu-cliques.md`. Não tente contornar com scripts que simulam clique.

### Controle de tela é opcional

Fica desligado por padrão e só serve para diálogo inesperado e para o plano B. O
fluxo normal não precisa dele. **Nunca clique em *Print plate* ou *Send*.**

No Codex, no Gemini e no Antigravity, o caminho é o
[Windows-MCP](https://github.com/CursorTouch/Windows-MCP), que acha botões pelo
nome via UI Automation. Ele não entra em nenhum manifesto: quem quiser liga à mão,
na configuração do agente, com a lista permitida abaixo. Fora dela ficam
PowerShell, Registry, FileSystem, Process e Scrape.

```
uvx --python 3.14 windows-mcp serve --tools "App,Click,Type,Shortcut,Snapshot,Screenshot,Wait"
```

Precisa de `uv` e Python 3.14 (o `uvx` baixa). **Dá acesso amplo ao PC:** o que
aparecer na tela fica ao alcance do modelo. Confira as flags no README da versão
instalada antes de usar.

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

| Agente | Onde | Como | Como verificar |
|---|---|---|---|
| Claude | extensão Autodesk Fusion do app, ou `claude mcp add` | `claude mcp add --transport http --scope user fusion http://127.0.0.1:27182/mcp` | `claude mcp list` |
| Codex | plugin, ou `~/.codex/config.toml` | `[mcp_servers.fusion]` com `url` | `codex mcp list` |
| Gemini CLI | extensão, ou `~/.gemini/settings.json` | `mcpServers.fusion.httpUrl` | `gemini mcp list` |
| Antigravity | plugin, ou `~/.gemini/config/mcp_config.json` | `mcpServers.fusion.serverUrl` | `agy mcp list` (não mostra MCP vindo de plugin) |

`python scripts/diagnostico.py` testa o servidor de verdade, com um `initialize`:

| `fusion.estado` | Quer dizer | O que fazer |
|---|---|---|
| `respondendo` | servidor certo no ar | seguir |
| `porta_fechada` | Fusion fechado ou servidor desligado | abrir o Fusion e ligar o servidor |
| `sem_mcp` | outro programa na porta | conferir `fusion.url_mcp` e o que usa a porta |

Se o diagnóstico responder e o agente não enxergar as ferramentas, o problema é a
configuração do agente: confira a chave abaixo e reinicie a sessão.

Cuidado com a chave: no Gemini, `url` significa SSE e não funciona aqui; no
Antigravity, `httpUrl` não existe.

O plugin do Claude não traz esse servidor de propósito: duplicaria a extensão
do app e daria erro de conexão com o Fusion fechado.

---

## MCP do Blender

Opcional: sem ele, o script roda por terminal (`blender-api.md`). Use o servidor
oficial do [Blender Lab](https://www.blender.org/lab/mcp-server/), Blender 5.1+: instale o
add-on pela página, ligue nas preferências e configure o servidor no agente pelas
instruções do [repositório](https://projects.blender.org/lab/blender_mcp). Ele não
entra nos manifestos, como o Windows-MCP: quem quiser liga à mão.

**Ele executa código do modelo no Blender sem proteção nenhuma.** O próprio Blender
Lab recomenda máquina virtual ou sistema sem dados sensíveis. Com terminal, `--background`
evita esse canal aberto.

---

## Impressora

`scripts/status.py` só lê: progresso, erros e o que está no AMS. Precisa de
`pip install -r scripts/requirements-lan.txt`, do IP e do serial em `impressora`, e
do access code, que **o próprio usuário** grava com `python scripts/config.py
codigo`, no terminal, para o código não passar pela conversa. Só rode com pedido do
usuário.

**Enviar peça não existe nesta skill.** Na A1 em modo normal, comando de impressão
por terceiros exige LAN Only e Developer Mode, que desligam nuvem e app Bambu Handy,
além de microSD na impressora. Se isso mudar um dia, o envio precisa de trava que
agente em aprovação automática não consiga passar sozinho: caixa nativa do Windows
com peça, tempo e gramas, e padrão em *Não*. Uma flag de linha de comando não serve.
