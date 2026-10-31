<div align="center">

# 🖨️ generate-bambu

**Peça uma peça. Seu agente modela no Fusion, valida, exporta o `.3mf` multicor e deixa pronto no Bambu Studio.**

*Uma skill para Claude, Codex, Gemini CLI e Antigravity que leva uma ideia da conversa até a mesa da impressora, com você aprovando cada passo importante.*

<br>

![Agent Skills](https://img.shields.io/badge/Agent-Skills-D97757?style=for-the-badge)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-6C47FF?style=for-the-badge)
![Autodesk Fusion](https://img.shields.io/badge/Autodesk-Fusion-FF6C00?style=for-the-badge&logo=autodesk&logoColor=white)
![Bambu Lab](https://img.shields.io/badge/Bambu%20Lab-A1%20%2B%20AMS%20Lite-00AE42?style=for-the-badge)

![Camada](https://img.shields.io/badge/camada-0%2C12%20mm-informational?style=flat-square)
![Volume](https://img.shields.io/badge/volume-250%C3%97250%C3%97250%20mm-informational?style=flat-square)
![Formato](https://img.shields.io/badge/sa%C3%ADda-.3mf%20multicor-informational?style=flat-square)
![Plataforma](https://img.shields.io/badge/plataforma-Windows-0078D4?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
[![CI](https://github.com/Grolla05/Generate-bambu/actions/workflows/ci.yml/badge.svg)](https://github.com/Grolla05/Generate-bambu/actions/workflows/ci.yml)
![Stars](https://img.shields.io/github/stars/Grolla05/Generate-bambu?style=flat-square)
![Last commit](https://img.shields.io/github/last-commit/Grolla05/Generate-bambu?style=flat-square)

[Como funciona](#-como-funciona) •
[Demonstração](#-demonstração) •
[Instalação](#-instalação) •
[Como usar](#-como-usar) •
[Decisões de design](#-decisões-de-design) •
[Limitações](#-limitações)

</div>

---

## 💡 Sobre

Este projeto nasceu de um problema simples: **comprei uma impressora 3D sem saber modelar nos mínimos detalhes**. Eu tinha só uma noção básica, e o gargalo nunca foi a máquina, foi o conhecimento de modelagem.

A solução foi transformar o processo em uma **skill**: uma sequência fixa de seis passos que vai do pedido em linguagem natural até o projeto fatiado no Bambu Studio. O agente cuida da parte repetitiva e técnica. As decisões que importam continuam sendo suas: **você aprova a forma antes de exportar e confirma antes de imprimir**.

> [!NOTE]
> A skill é focada em **geometria construída**: placas, letreiros, chaveiros, lembrancinhas, ímãs, vasos, potes, caixas com tampa, suportes, engrenagens e peças com rosca ou encaixe. Rostos, corpos e animais realistas ficam fora do método (veja [Limitações](#-limitações)).

---

## ⚙️ Como funciona

```mermaid
flowchart LR
    A["💬 Você pede a peça"] --> B["🧩 1. Modela no Fusion"]
    B --> C["✅ Valida e mostra"]
    C --> D{"👤 2. Você aprova?"}
    D -- "pede ajuste" --> B
    D -- "OK" --> E["📦 3. Exporta .3mf"]
    E --> F["🖥️ 4. Abre o Bambu Studio"]
    F --> G["🔍 5. Carrega e confere"]
    G --> H{"🖨️ 6. Posso imprimir?"}
    H -- "sim" --> I["🎉 Impressão"]
```

| # | Passo | O que acontece |
|:-:|---|---|
| **1** | 🧩 **Modelar, validar e mostrar** | O agente cria um design **paramétrico** no Fusion, via script. Cada cor é um corpo separado (`slotN_descricao`). Roda uma validação automática e deixa a peça aberta no Fusion para você girar e inspecionar. |
| **2** | 👤 **Esperar o OK** | Parada obrigatória. Se pedir ajuste, o agente muda os parâmetros no **mesmo documento**, valida de novo e salva uma nova versão. |
| **3** | 📦 **Exportar o `.3mf`** | Só depois do OK. Um único `.3mf` com **um objeto por slot do AMS**, camada de 0,12 mm. Sem STL, sem ZIP, sem pasta de arquivos soltos. |
| **4** | 🖥️ **Abrir o Bambu Studio** | O agente abre o programa e trata janelas de update, login e seleção de impressora. Sem controle de tela, ele passa um roteiro para você. |
| **5** | 🔍 **Carregar e conferir** | Abre o projeto, confere cores, **dimensões** (contra o que o Fusion mostrou) e filamentos, e fatia. |
| **6** | 🖨️ **Perguntar antes de imprimir** | Mostra o **tempo estimado** e os **gramas por filamento**, e só manda imprimir com a sua resposta. |

### ✅ O que a validação garante (passo 1)

- Todo corpo é sólido e tem o prefixo `slotN_`
- Alturas em **múltiplos da camada** (0,12 mm)
- Peça inteira dentro de **250 × 250 × 250 mm** (Bambu Lab A1)
- No máximo **4 slots** de cor (AMS Lite)
- **Nenhuma interferência** entre corpos e nenhuma cor padrão do Fusion
- Espessuras mínimas e balanços conferidos contra as regras de FDM da A1

---

## 🎬 Demonstração

> [!TIP]
> Substitua as imagens abaixo pelas suas capturas. Basta salvar os arquivos em `docs/images/` com os nomes indicados e o README passa a exibi-los.

### Do pedido à peça

<div align="center">

<img src="docs/images/demo.gif" alt="GIF mostrando o fluxo completo: do pedido ao agente até a peça fatiada no Bambu Studio" width="85%">

<sub><i>Fluxo completo, do pedido ao slice (GIF)</i></sub>

</div>

### Passo a passo

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/images/01-pedido.png" alt="Conversa com o agente pedindo a peça" width="100%"><br>
      <b>1. O pedido</b><br>
      <sub>Linguagem natural, sem precisar saber modelar</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/images/02-fusion-modelagem.png" alt="Peça paramétrica aberta no Autodesk Fusion" width="100%"><br>
      <b>2. Modelagem no Fusion</b><br>
      <sub>Design paramétrico, um corpo por cor</sub>
    </td>
  </tr>
  <tr>
    <td align="center" colspan="2">
      <img src="docs/images/05-bambu-studio-cores.png" alt="Bambu Studio com a prévia colorida do projeto" width="50%"><br>
      <b>3. Bambu Studio</b><br>
      <sub>Cores por slot e dimensões conferidas</sub>
    </td>
  </tr>
</table>

### Resultado

<div align="center">

<img src="docs/images/peca-impressa.jpg" alt="Foto da peça impressa em multicor" width="60%">

<sub><i>A peça final impressa na Bambu Lab A1 com AMS Lite</i></sub>

</div>

---

## 📋 Requisitos

| Requisito | Detalhe |
|---|---|
| 🤖 **Agente** | Claude, Codex, Gemini CLI ou Antigravity |
| 🧩 **Autodesk Fusion** | Instalado, com o **servidor MCP local** ativo em Preferences → General → API → Fusion MCP Server (*Apply* e depois *OK*). A skill modela via `fusion_mcp_execute` |
| 🖨️ **Impressora** | Bambu Lab **A1** com **AMS Lite** (até 4 cores) |
| 🖥️ **Bambu Studio** | Instalado, com a interface em **inglês** (testado na 02.08) |
| 🪟 **Sistema** | Windows (os caminhos e o fluxo do Bambu Studio foram testados nele) |
| 🖱️ **Controle do computador** | Opcional. Com ele, o agente opera o Bambu Studio nos passos 4 a 6. Sem ele, o agente passa um roteiro e você informa tamanho, tempo e gramas |

> [!IMPORTANT]
> Os passos 1 a 3 (modelar, validar e exportar) só dependem do Fusion. O que muda entre agentes está em [`referencias/agentes.md`](skills/generate-bambu/referencias/agentes.md).

> [!WARNING]
> `D:\Bambu Lab\projeto\`, o projeto `Bubble Studio 3D` e a nota de catálogo são padrões do autor. Ajuste conforme a seção Configuração.

---

## 🚀 Instalação

Use **um canal só por agente**. Plugin e cópia da pasta juntos criam skills duplicadas.

### Claude

```bash
claude plugin marketplace add Grolla05/Generate-bambu
```

```bash
claude plugin install generate-bambu@grolla05-plugins
```

No app desktop, adicione `Grolla05/Generate-bambu` como marketplace pela tela de plugins. A chamada direta é `/generate-bambu:generate-bambu`.

O plugin não traz o MCP do Fusion: use a extensão Autodesk Fusion do app, ou rode `instalar.ps1 -McpClaude` para registrá-lo no Claude Code.

### Codex

```bash
codex plugin marketplace add Grolla05/Generate-bambu
```

```bash
codex plugin add generate-bambu@grolla05-plugins
```

No app, o mesmo marketplace aparece na tela de plugins. O plugin já traz o MCP do Fusion.

### Gemini CLI

```bash
gemini extensions install https://github.com/Grolla05/Generate-bambu
```

A extensão já traz o MCP do Fusion. O Gemini CLI parou de atender contas individuais em junho de 2026: sem chave de API ou conta enterprise, use o Antigravity.

### Antigravity

```bash
git clone https://github.com/Grolla05/Generate-bambu
```

```bash
agy plugin install ./Generate-bambu
```

O plugin já traz o MCP do Fusion.

### Instalador para Windows

Sem plugin, o `instalar.ps1` detecta os agentes, copia a skill para a pasta de cada um e grava a configuração do MCP. Ele pula o agente que já tem plugin ou extensão, mostra o plano e pede confirmação.

```bash
git clone https://github.com/Grolla05/Generate-bambu
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Generate-bambu\instalar.ps1 -Simular
```

| Opção | O que faz |
|---|---|
| `-Simular` | Só mostra o plano |
| `-Agentes codex,antigravity` | Limita aos agentes citados: `claude`, `codex`, `gemini`, `antigravity`, `agy` |
| `-Sim` | Aplica sem perguntar |
| `-Desinstalar` | Remove só o que o script instalou |
| `-McpClaude` | Registra o MCP do Fusion no Claude Code |

> [!NOTE]
> O script faz backup de cada arquivo que altera (`.bak-<data>`), ao lado do original. Esses arquivos têm tokens: não os compartilhe. Arquivo com comentários ou JSON inválido fica intacto, e o script pede para adicionar o MCP à mão. Feche o app do Codex antes de rodar.

### ✔️ Conferindo a instalação

```bash
claude plugin details generate-bambu
```

```bash
codex plugin list
```

```bash
gemini extensions list
```

```bash
agy plugin list --json
```

### 🔄 Atualizando

Quem tem a versão 1.0.0 instalada recebe a nova estrutura pelos mesmos comandos.

```bash
claude plugin marketplace update grolla05-plugins
```

```bash
claude plugin update generate-bambu@grolla05-plugins
```

```bash
codex plugin marketplace upgrade grolla05-plugins
```

```bash
codex plugin add generate-bambu@grolla05-plugins
```

```bash
gemini extensions update generate-bambu
```

No Antigravity, atualize o clone e rode `agy plugin install` de novo. Com o instalador, atualize o clone e rode o script de novo.

---

## 🕹️ Como usar

Com a skill instalada e o Fusion aberto, basta pedir. Ela é acionada sozinha em qualquer pedido de criar, desenhar ou modelar uma peça para impressão 3D, em português ou inglês.

### Exemplos de pedidos

```text
Faz um chaveiro retangular de 60 x 30 mm com o nome "Felipe" em relevo,
base azul e letras brancas.
```

```text
Preciso de um porta-copo redondo de 90 mm com um brasão em relevo de duas cores.
```

```text
Modela um vaso de 80 mm de altura com parede de 2 mm, em uma cor só.
```

```text
Cria uma lembrancinha de 70 x 50 mm com a data "12/10" e uma moldura em dourado.
```

### O que esperar na conversa

1. O agente confirma o que vai modelar e quantas cores a peça tem.
2. A peça aparece **aberta no Fusion**, com as dimensões finais, a lista de slots (cor, altura, camadas) e os ajustes de camada que foram feitos.
3. Ele pergunta se está aprovado. Você pede ajustes quantas vezes quiser.
4. Com o OK, exporta, abre o Bambu Studio, fatia e mostra **tempo e gramas**. Sem controle de tela, ele entrega o `.3mf` e um roteiro para você.
5. Ele pergunta **"posso mandar imprimir?"** e espera a sua resposta.

---

## 🧠 Decisões de design

| Decisão | Por quê |
|---|---|
| 🧩 **Modelagem só pelo Fusion** | Nada de SVG, malha gerada em código ou OpenSCAD. A peça precisa ser editável de verdade: mudar uma medida é editar um parâmetro, não refazer o desenho. |
| 📐 **Alturas em múltiplos da camada** | O slicer não sabe fazer 0,8 mm numa camada de 0,12 mm. A skill arredonda (0,8 mm vira 0,84 mm) e **avisa cada ajuste**, para você aprovar a peça que realmente vai sair. |
| 🎨 **Um corpo por cor, um objeto por slot** | A cor vai pintada na malha do `.3mf`, e cada slot do AMS vira um objeto. O Bambu Studio já abre o projeto com as cores certas. |
| 🛑 **Duas paradas obrigatórias** | Aprovar a forma (passo 2) e autorizar a impressão (passo 6). Plástico e horas de máquina só são gastos com a sua confirmação. |
| 👁️ **Nada "de memória"** | Se o agente fala do que está na tela do Fusion ou do Bambu Studio, é porque capturou a tela e leu, ou porque você informou. Se não conseguiu, ele diz que não conseguiu. |
| 🔌 **Um repositório, vários agentes** | A skill mora em `skills/` e cada agente tem seu manifesto. Os testes conferem que nome, versão e URL do MCP são iguais em todos. |
| 🧭 **Capacidades, não ferramentas** | O `SKILL.md` descreve a ação; `referencias/agentes.md` traduz para a ferramenta de cada agente. |
| 📏 **Conferência de unidade** | As dimensões no Bambu Studio têm que bater com o Fusion. Uma peça 1000× maior ou menor indica erro de unidade, e a correção é refazer a exportação, nunca escalar no slicer. |
| ⚖️ **Design de terceiros fica de fora** | Personagens, marcas, carros e logos pertencem a outras pessoas. A skill oferece um desenho **original** no lugar. |

---

## 🗂️ Estrutura do repositório

```text
Generate-bambu/
├── .agents/plugins/
│   └── marketplace.json            # Codex: catálogo
├── .antigravity-plugin/
│   └── plugin.json                 # Antigravity: manifesto
├── .claude-plugin/
│   ├── marketplace.json            # Claude: catálogo
│   └── plugin.json                 # Claude: manifesto
├── .codex-plugin/
│   └── plugin.json                 # Codex: manifesto
├── skills/
│   └── generate-bambu/
│       ├── SKILL.md                # o fluxo de seis passos
│       ├── agents/
│       │   └── openai.yaml         # Codex: dependência do MCP e invocação
│       ├── referencias/
│       │   ├── agentes.md          # capacidades, instalação e MCP por agente
│       │   ├── fusion-api.md       # receitas testadas de script, validação e exportação
│       │   ├── fdm-a1.md           # espessuras, folgas, orientação e balanços da A1
│       │   └── limites.md          # triagem do que cabe (ou não) no método
│       └── helpers/
│           └── agrupar_3mf.py      # agrupa o 3MF em um objeto por slot
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI: lint, validação da skill, testes e instalador
├── tests/                          # testes do helper, da documentação, dos manifestos e do instalador
├── docs/
│   └── images/                     # capturas de tela e GIFs da demonstração
├── gemini-extension.json           # Gemini CLI: manifesto
├── instalar.ps1                    # instalador para Windows
├── mcp.json                        # MCP do Fusion para Codex e Antigravity
├── pyproject.toml                  # configuração do pytest e do ruff
├── requirements-dev.txt            # pytest e ruff
├── LICENSE
└── README.md
```

---

## ⚙️ Configuração

Alguns caminhos do fluxo são pessoais e podem ser ajustados no `SKILL.md`:

| O quê | Padrão | Observação |
|---|---|---|
| Pasta de saída dos `.3mf` | `D:\Bambu Lab\projeto\` | Troque pela pasta que você usa |
| Projeto no Fusion | `Bubble Studio 3D` | Criado automaticamente se não existir |
| Altura de camada | `0,12 mm` | Parâmetro `camada` no início do design |
| Registro no Obsidian | opcional | A skill pode anotar tempo e gramas de cada peça numa nota de catálogo. Remova a seção *"Depois: registrar no vault"* se não usar. |

---

## ⚠️ Limitações

- **Só geometria construída.** O Fusion faz booleana, fillet, chamfer, shell, rosca e texto. Rosto, corpo e animal realista não cabem no método.
- **Até 4 cores**, pelos 4 slots do AMS Lite. Acima de 2 cores, o custo de purga de filamento sobe.
- **Volume de 250 × 250 × 250 mm**, o limite da Bambu Lab A1.
- **O perfil de impressão não vem no `.3mf`.** A altura de camada de 0,12 mm é ajustada no Bambu Studio a cada projeto.
- **Controle do Bambu Studio por tela é frágil.** Se um clique não faz efeito, a skill para, descreve o que está na tela e pergunta, em vez de repetir às cegas. Gemini CLI e Antigravity seguem o roteiro manual.
- **Licença do Fusion.** Com a licença *Education* (uso não comercial), as peças servem para uso próprio e presentes. Para **vender** o que for impresso, revise a licença do Fusion antes.

---

## 🧪 Testes e CI

A cada push e pull request, o GitHub Actions ([`ci.yml`](.github/workflows/ci.yml)) roda:

| Job | O que valida |
|---|---|
| **Lint** | `ruff check` em todo o código Python e `agentskills validate` na skill |
| **Testes** | `compileall` e `pytest` em Python **3.10, 3.11, 3.12 e 3.13** |
| **Instalador** | `instalar.ps1` no PowerShell 5.1 do Windows, contra uma pasta de usuário falsa |

Os testes cobrem o `agrupar_3mf.py` com 3MFs sintéticos (agrupamento por slot, volumes, malhas fechadas, cores, transformações e as recusas de entrada inválida), a sintaxe dos trechos Python da documentação, a consistência dos manifestos de cada agente e o instalador.

Para rodar localmente:

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

---

## 🛣️ Roadmap

- [ ] Placa de calibração para medir a folga real de processo da máquina
- [ ] Suporte a outras impressoras da linha Bambu Lab (A1 mini, P1S)
- [ ] Biblioteca de peças-base (chaveiro, porta-copo, placa) como pontos de partida
- [ ] Opção de salvar o perfil de impressão junto com o projeto
- [ ] Versão em inglês da documentação

---

## 🤝 Contribuindo

Ideias, correções e novos tipos de peça são bem-vindos. Abra uma *issue* descrevendo o caso ou envie um *pull request*.

## 📄 Licença

Distribuído sob a licença MIT. Veja o arquivo [`LICENSE`](LICENSE).

## 👤 Autor

**Felipe Grolla**, estudante de Engenharia de Controle e Automação na PUC-Campinas.

[![GitHub](https://img.shields.io/badge/GitHub-Grolla05-181717?style=flat-square&logo=github)](https://github.com/Grolla05)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-felipegrolla-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/felipegrolla)

<div align="center">

<sub>Feito com 🧩 Fusion, 🖨️ Bambu Lab e 🤖 Claude</sub>

</div>
