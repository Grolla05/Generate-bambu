<div align="center">

# 🖨️ generate-bambu

**🇺🇸 English** · [🇧🇷 Português](README.pt-BR.md)

**Ask for a part. Your agent models it in Fusion or Blender, validates it, exports a multicolor `.3mf`, slices it and leaves it ready in Bambu Studio.**

*A skill for Claude, Codex, Gemini CLI and Antigravity that takes an idea from the chat to the print bed, with you approving every step that matters.*

<br>

![Agent Skills](https://img.shields.io/badge/Agent-Skills-D97757?style=for-the-badge)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-6C47FF?style=for-the-badge)
![Autodesk Fusion](https://img.shields.io/badge/Autodesk-Fusion-FF6C00?style=for-the-badge&logo=autodesk&logoColor=white)
![Bambu Lab](https://img.shields.io/badge/Bambu%20Lab-A1%20%2B%20AMS%20Lite-00AE42?style=for-the-badge)

![Layer](https://img.shields.io/badge/layer-0.12%20mm-informational?style=flat-square)
![Volume](https://img.shields.io/badge/volume-250%C3%97250%C3%97250%20mm-informational?style=flat-square)
![Output](https://img.shields.io/badge/output-multicolor%20.3mf-informational?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
[![CI](https://github.com/Grolla05/Generate-bambu/actions/workflows/ci.yml/badge.svg)](https://github.com/Grolla05/Generate-bambu/actions/workflows/ci.yml)
![Stars](https://img.shields.io/github/stars/Grolla05/Generate-bambu?style=flat-square)
![Last commit](https://img.shields.io/github/last-commit/Grolla05/Generate-bambu?style=flat-square)

[How it works](#%EF%B8%8F-how-it-works) •
[Demo](#-demo) •
[Installation](#-installation) •
[Usage](#%EF%B8%8F-usage) •
[Design decisions](#-design-decisions) •
[Limitations](#%EF%B8%8F-limitations)

</div>

---

## 💡 About

This project started from a simple problem: **I bought a 3D printer without knowing how to model in fine detail**. I only had a basic idea, and the bottleneck was never the machine, it was modeling know-how.

The answer was to turn the process into a **skill**: a fixed six-step sequence that goes from a plain-language request to a sliced project in Bambu Studio. The agent handles the repetitive, technical part. The decisions that matter stay with you: **you approve the shape before export and you confirm before printing**.

> [!NOTE]
> **Constructed geometry** (plates, signs, keychains, magnets, vases, boxes, brackets, gears, threaded or snap-fit parts) goes to Fusion. **Stylized organic shapes** (low-poly animals and figures) go to Blender. Realism is out of scope (see [Limitations](#%EF%B8%8F-limitations)).
>
> The skill itself speaks Portuguese (its instructions and messages are in pt-BR), but it triggers on requests in English as well.

---

## ⚙️ How it works

```mermaid
flowchart LR
    A["💬 You ask for a part"] --> B["🧩 1. Model in Fusion or Blender"]
    B --> C["✅ Validate and show"]
    C --> D{"👤 2. Approved?"}
    D -- "asks for changes" --> B
    D -- "OK" --> E["📦 3. Export .3mf"]
    E --> F["🔪 4. Slice by script"]
    F --> G["🔍 5. Open and check"]
    G --> H["⏱️ 6. Time and grams"]
    H --> I["👤 You click Print plate"]
```

| # | Step | What happens |
|:-:|---|---|
| **1** | 🧩 **Model, validate and show** | The agent builds a **parametric** design in Fusion, by script. Each color is a separate body (`slotN_description`). An automatic validation runs and the part stays open in Fusion for you to rotate and inspect. |
| **2** | 👤 **Wait for the OK** | Mandatory stop. If you ask for changes, the agent edits the parameters in the **same document**, validates again and saves a new version. |
| **3** | 📦 **Export the `.3mf`** | Only after the OK. A single `.3mf` with **one object per AMS slot**, 0.12 mm layers. No STL, no ZIP, no folder of loose files. |
| **4** | 🔪 **Slice by script** | `scripts/fatiar.py` uses the Bambu Studio CLI, with no clicks and no dialogs, and checks layer height, filaments and **dimensions**. Works in any agent with a terminal. |
| **5** | 🔍 **Open and check** | The sliced file opens in Bambu Studio already colored, for you to check. |
| **6** | ⏱️ **Ready to print** | Shows the **estimated time** and **grams per filament**. **The skill never prints:** you are the one who clicks *Print plate*. |

### ✅ What validation guarantees (step 1)

- Every body is solid and has the `slotN_` prefix
- Heights are **multiples of the layer height** (0.12 mm)
- The whole part fits in **250 × 250 × 250 mm** (Bambu Lab A1)
- At most **4 color slots** (AMS Lite)
- **No interference** between bodies and no default Fusion color
- Minimum thicknesses and overhangs checked against the A1 FDM rules

### 🧱 Base parts

For the most common requests the agent doesn't start from scratch: [`modelos/`](skills/generate-bambu/modelos/) has five scripts already run and validated in Fusion (keychain, coaster, sign with text, vase, box with lid). It changes only the parameter block at the top and runs the file.

---

## 🎬 Demo

> [!NOTE]
> Screenshots and a GIF of the full flow are on the way. Meanwhile, the flowchart in [How it works](#%EF%B8%8F-how-it-works) shows each step. The list of captures still missing is in [`docs/images/CAPTURAS.md`](docs/images/CAPTURAS.md).

---

## 📋 Requirements

| Requirement | Detail |
|---|---|
| 🤖 **Agent** | Claude, Codex, Gemini CLI or Antigravity |
| 🧩 **Autodesk Fusion** | For exact-dimension parts. Installed, with the **local MCP server** enabled under Preferences → General → API → Fusion MCP Server (*Apply*, then *OK*) |
| 🐒 **Blender** | Optional, for stylized organic shapes. 5.1 or newer; runs from the terminal, MCP optional |
| 🖨️ **Printer** | Bambu Lab **A1** with **AMS Lite** (up to 4 colors) |
| 🖥️ **Bambu Studio** | Installed (tested on 02.08.03.66) |
| 🐍 **Python** | 3.10 or newer, to slice through the CLI. Without it, use the [click-based plan B](skills/generate-bambu/referencias/bambu-cliques.md) |
| 🪟 **OS** | Windows (paths and the Bambu Studio flow were tested on it) |
| 🖱️ **Computer control** | Optional, only for plan B. Never clicks *Print plate* |

> [!IMPORTANT]
> What changes between agents is in [`referencias/agentes.md`](skills/generate-bambu/referencias/agentes.md).

---

## 🚀 Installation

Use **only one channel per agent**. Installing the plugin and copying the folder creates duplicate skills.

### Claude

```bash
claude plugin marketplace add Grolla05/Generate-bambu
```

```bash
claude plugin install generate-bambu@grolla05-plugins
```

In the desktop app, add `Grolla05/Generate-bambu` as a marketplace from the plugins screen. The direct call is `/generate-bambu:generate-bambu`.

The plugin does not ship the Fusion MCP: use the app's Autodesk Fusion extension, or run `instalar.ps1 -McpClaude` to register it in Claude Code.

### Codex

```bash
codex plugin marketplace add Grolla05/Generate-bambu
```

```bash
codex plugin add generate-bambu@grolla05-plugins
```

In the app, the same marketplace shows up on the plugins screen. The plugin already ships the Fusion MCP.

### Gemini CLI

```bash
gemini extensions install https://github.com/Grolla05/Generate-bambu
```

The extension already ships the Fusion MCP. Gemini CLI stopped serving individual accounts in June 2026: without an API key or an enterprise account, use Antigravity.

### Antigravity

```bash
git clone https://github.com/Grolla05/Generate-bambu
```

```bash
agy plugin install ./Generate-bambu
```

The plugin already ships the Fusion MCP.

### Windows installer

Without a plugin, `instalar.ps1` detects your agents, copies the skill into each one's folder and writes the MCP configuration. It skips any agent that already has the plugin or extension, shows the plan and asks for confirmation.

```bash
git clone https://github.com/Grolla05/Generate-bambu
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Generate-bambu\instalar.ps1 -Simular
```

| Option | What it does |
|---|---|
| `-Simular` | Only shows the plan (dry run) |
| `-Agentes codex,antigravity` | Limits to the listed agents: `claude`, `codex`, `gemini`, `antigravity`, `agy` |
| `-Sim` | Applies without asking |
| `-Desinstalar` | Removes only what the script installed |
| `-McpClaude` | Registers the Fusion MCP in Claude Code |

> [!NOTE]
> The script backs up every file it changes (`.bak-<date>`), next to the original. These files contain tokens: don't share them. A file with comments or invalid JSON is left untouched, and the script asks you to add the MCP by hand. Close the Codex app before running it.

### ✔️ Checking the installation

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

### 🔄 Updating

If you have version 1.0.0 installed, the same commands bring in the new structure.

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

In Antigravity, update the clone and run `agy plugin install` again. With the installer, update the clone and run the script again.

---

## 🕹️ Usage

With the skill installed and Fusion open, just ask. It triggers on its own for any request to create, draw or model a part for 3D printing, in Portuguese or English.

### Example requests

```text
Make a 60 x 30 mm rectangular keychain with the name "Felipe" raised,
blue base and white letters.
```

```text
I need a round 90 mm coaster with a two-color raised crest.
```

```text
Model an 80 mm tall vase with a 2 mm wall, in a single color.
```

```text
Create a 70 x 50 mm party favor with the date "12/10" and a gold frame.
```

### What to expect in the conversation

1. The agent confirms what it is going to model and how many colors the part has.
2. The part appears **open in Fusion**, with the final dimensions, the list of slots (color, height, layers) and any layer adjustments made.
3. It asks whether you approve. Ask for changes as many times as you want.
4. With the OK, it exports, slices and shows **time and grams**. Printing is up to you, in Bambu Studio.
5. It asks **"can I send it to print?"** and waits for your answer.

---

## 🧠 Design decisions

| Decision | Why |
|---|---|
| 🧩 **Modeling only in Fusion (or Blender)** | No SVG, code-generated mesh or OpenSCAD. The part has to be truly editable: changing a dimension means editing a parameter, not redrawing. |
| 📐 **Heights in multiples of the layer** | The slicer can't make 0.8 mm with 0.12 mm layers. The skill rounds (0.8 mm becomes 0.84 mm) and **reports every adjustment**, so you approve the part that will actually come out. |
| 🎨 **One body per color, one object per slot** | The color is painted on the `.3mf` mesh, and each AMS slot becomes one object. Bambu Studio opens the project with the right colors. |
| 🛑 **Two mandatory stops** | Approve the shape (step 2) and authorize printing (step 6). Plastic and machine hours are only spent with your confirmation. |
| 👁️ **Nothing "from memory"** | If the agent talks about what is on screen in Fusion or Bambu Studio, it captured the screen and read it, or you told it. If it couldn't, it says so. |
| 🔌 **One repository, many agents** | The skill lives in `skills/` and each agent has its own manifest. Tests check that name, version and MCP URL match across all of them. |
| 🧭 **Capabilities, not tools** | `SKILL.md` describes the action; `referencias/agentes.md` translates it into each agent's tool. |
| 📏 **Unit check** | Dimensions in Bambu Studio must match Fusion. A part 1000× bigger or smaller means a unit error, and the fix is to redo the export, never to scale in the slicer. |
| ⚖️ **Third-party designs stay out** | Characters, brands, cars and logos belong to other people. The skill offers an **original** design instead. |
| 🧪 **Stops are evaluated per agent** | [`evals/`](evals/) has standard requests and a scoring rubric to compare how each agent respects the stops, where models diverge the most. |

---

## 🗂️ Repository structure

```text
Generate-bambu/
├── .agents/plugins/
│   └── marketplace.json            # Codex: catalog
├── .antigravity-plugin/
│   └── plugin.json                 # Antigravity: manifest
├── .claude-plugin/
│   ├── marketplace.json            # Claude: catalog
│   └── plugin.json                 # Claude: manifest
├── .codex-plugin/
│   └── plugin.json                 # Codex: manifest
├── skills/
│   └── generate-bambu/
│       ├── SKILL.md                # the six-step flow
│       ├── config.example.json     # template for the local configuration
│       ├── agents/
│       │   └── openai.yaml         # Codex: MCP dependency and invocation
│       ├── referencias/
│       │   ├── agentes.md          # capabilities, installation and MCP per agent
│       │   ├── fusion-api.md       # tested recipes for scripting, validation and export
│       │   ├── blender-api.md      # tested recipes for organic shapes
│       │   ├── bambu-cliques.md    # click-based plan B
│       │   ├── fdm-a1.md           # A1 thicknesses, clearances, orientation and overhangs
│       │   └── limites.md          # triage of what fits (or not) the method
│       ├── modelos/                # base parts tested in Fusion, parameters at the top
│       ├── helpers/
│       │   ├── agrupar_3mf.py      # groups the 3MF into one object per slot
│       │   └── blender_3mf.py      # runs inside Blender: validates and exports
│       └── scripts/
│           ├── config.py           # local configuration and access code
│           ├── diagnostico.py      # what is ready on this machine
│           ├── detectar_modeladores.py  # which modeler to use
│           ├── fatiar.py           # slices through the Bambu Studio CLI
│           ├── projeto_bambu.py    # builds the native project
│           ├── perfis.py           # resolves the installed profiles
│           ├── bambu_3mf.py        # reads time and grams from the sliced file
│           ├── registro.py         # local log of every sliced part
│           └── status.py           # printer status, read-only
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI: lint, skill validation, tests and installer
├── evals/                          # cases and rubric to compare agents
├── tests/                          # tests for the helper, docs, manifests and installer
├── docs/
│   └── images/                     # screenshots and GIFs for the demo
├── gemini-extension.json           # Gemini CLI: manifest
├── instalar.ps1                    # Windows installer
├── mcp.json                        # Fusion MCP for Codex and Antigravity
├── pyproject.toml                  # pytest and ruff configuration
├── requirements-dev.txt            # pytest and ruff
├── LICENSE
├── README.md                       # English
└── README.pt-BR.md                 # Portuguese
```

---

## ⚙️ Configuration

The configuration lives in `~/.generate-bambu/config.json`, outside the skill, because updating the plugin replaces its folder. The template is [`config.example.json`](skills/generate-bambu/config.example.json):

```bash
python skills/generate-bambu/scripts/config.py definir pasta_saida "D:/Print3D"
```

The printer access code is only needed for `status.py`. Run `config.py codigo` yourself, in the terminal, so it never goes through the chat.

| What | Default | Note |
|---|---|---|
| Output folder for `.3mf` files | asked on first use | Key `pasta_saida` |
| Bambu Studio profiles | A1, `0.12mm Fine`, PLA Basic | Section `bambu_studio` |
| Modeler | chosen per part | `modelador.preferido` breaks ties |
| Fusion project | `generate-bambu` | Key `fusion.projeto`; created automatically if missing |
| Printer | A1 | `config.py maquina "A1 mini"` or `"P1S"` writes limits and profiles together; those two were checked only up to slicing |
| Layer height | `0.12 mm` | `camada` parameter at the start of the design |
| Profile | none | `~/.generate-bambu/perfil.md`, with your own context. Template in [`perfil.example.md`](skills/generate-bambu/perfil.example.md) |

---

## ⚠️ Limitations

- **Constructed geometry only.** Fusion does booleans, fillets, chamfers, shells, threads and text. Faces, bodies and realistic animals don't fit the method.
- **Up to 4 colors**, from the 4 AMS Lite slots. Above 2 colors, filament purge cost goes up.
- **250 × 250 × 250 mm volume**, the Bambu Lab A1 limit.
- **The print profile doesn't travel inside the `.3mf`.** The 0.12 mm layer height is set in Bambu Studio for each project.
- **Screen control is optional and fragile.** It only comes in as plan B, if script slicing fails. If a click has no effect, the skill stops and asks instead of retrying blindly. It never clicks *Print plate*.
- **A multicolor part that covers almost the whole bed on both axes is refused:** there is no room for the purge tower.
- **Fusion license.** With the *Education* license (non-commercial use), parts are fine for personal use and gifts. To **sell** what you print, review your Fusion license first.

---

## 🧪 Tests and CI

On every push and pull request, GitHub Actions ([`ci.yml`](.github/workflows/ci.yml)) runs:

| Job | What it checks |
|---|---|
| **Lint** | `ruff check` on all Python code and `agentskills validate` on the skill |
| **Tests** | `compileall` and `pytest` on Python **3.10, 3.11, 3.12 and 3.13** |
| **Installer** | `instalar.ps1` on Windows PowerShell 5.1, against a fake user folder |

Tests cover `agrupar_3mf.py` with synthetic 3MFs (grouping by slot, volumes, closed meshes, colors, transforms and rejection of invalid input), the syntax of the Python snippets in the docs, the shape of the base parts, the evaluation cases, consistency of each agent's manifest, and the installer.

To run locally:

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

---

## 🛣️ Roadmap

- [ ] Calibration plate to measure the machine's real process clearance
- [x] Support for other Bambu Lab printers (A1 mini and P1S, checked only up to slicing)
- [x] Print profile saved with the project
- [ ] Verify script export against real Fusion
- [x] Library of base parts (keychain, coaster, sign, vase, box) as starting points
- [x] Evaluations comparing how each agent respects the mandatory stops ([`evals/`](evals/))
- [x] English version of the documentation
- [ ] Demo screenshots and GIF

---

## 🤝 Contributing

Ideas, fixes and new part types are welcome. Open an *issue* describing the case or send a *pull request*.

## 📄 License

Distributed under the MIT license. See [`LICENSE`](LICENSE).

## 👤 Author

**Felipe Grolla**, Control and Automation Engineering student at PUC-Campinas.

[![GitHub](https://img.shields.io/badge/GitHub-Grolla05-181717?style=flat-square&logo=github)](https://github.com/Grolla05)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-felipegrolla-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/felipegrolla)

<div align="center">

<sub>Made with 🧩 Fusion, 🖨️ Bambu Lab and 🤖 Claude</sub>

</div>
