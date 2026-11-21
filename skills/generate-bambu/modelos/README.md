# Peças-base

Pontos de partida já rodados no Fusion. Quando o pedido casa com uma destas
peças, parta do arquivo em vez de escrever o script do zero: copie, mude **só o
bloco de parâmetros** do topo e rode o arquivo inteiro com `fusion_mcp_execute`
(`featureType: "script"`). Cada script abre um documento novo, cria os *User
Parameters* com as alturas em `N * camada`, nomeia os corpos `slotN_` com a cor
`cor_#rrggbb`, enquadra a vista e imprime um resumo em JSON. Nenhum exporta nada:
depois dele vêm a validação (1c), a conferência (1d) e o OK do passo 2, como em
qualquer peça.

Conferidas em 21/11/2026 no Fusion 2706.1.17 (Python 3.14): todas deram `ok: true`
na validação de `referencias/fusion-api.md`, com os parâmetros padrão.

| Arquivo | Peça | Slots | Parâmetros principais | Pegadinha que já resolve |
|---|---|---|---|---|
| `chaveiro.py` | placa com furo e nome em relevo, 60 × 30 mm | 1 placa, 2 nome | `NOME`, `LARGURA`, `ALTURA`, `FURO` | nome encolhe até caber ao lado do furo; para abaixo de 6 mm |
| `porta_copo.py` | disco Ø90 com borda e texto em relevo | 1 disco, 2 borda + texto | `DIAMETRO`, `TEXTO`, `BORDA`, `CHANFRO` | chanfro só na aresta de baixo, antes do relevo |
| `placa_texto.py` | letreiro 150 × 50 mm com moldura | 1 placa, 2 moldura, 3 texto se a cor for outra | `TEXTO`, `LARGURA`, `ALTURA`, `COR_TEXTO` | texto que transborda a caixa do `setAsMultiLine`; slot do texto segue a cor |
| `vaso.py` | vaso de revolução, 80 mm | 1 vaso | `ALTURA_CAMADAS`, `RAIO_BASE`, `RAIO_TOPO`, `PAREDE` | Y do sketch é −Z no plano XZ; recusa parede acima de 45° |
| `caixa_tampa.py` | caixa 80 × 60 × 40 mm e tampa de encaixe | 1 caixa, 2 tampa | `COMPRIMENTO`, `LARGURA`, `ALTURA_CAMADAS`, `FOLGA` | aba da tampa por dentro da parede menos a `folga`; peças lado a lado na mesa |

## Regras dos modelos

- Medidas em **mm** no bloco de parâmetros; o script converte para centímetro.
- Altura nunca entra solta: é `*_CAMADAS`, multiplicada por 0,12 mm.
- Uma cor por slot. Mudar a cor de um elemento para outra já usada move o corpo de
  slot só onde o script prevê (`placa_texto.py`); nos outros, mantenha as cores
  diferentes por slot.
- Texto encolhe até caber e para com erro abaixo de `TEXTO_MIN_MM` (6 mm, o mínimo
  de `fdm-a1.md` para relevo).
- Na conferência, o Fusion com **Y para cima** mostra o topo da peça na vista
  `front`, não em `top`.

## Modelo novo

Mesmo esqueleto dos existentes: docstring dizendo slots e uso, bloco de
parâmetros entre as linhas `# ---`, `run(context)` que abre documento novo e
termina em `app.activeViewport.fit()`. Rode no Fusion, valide com `ok: true`,
confira as vistas, acrescente a linha na tabela acima e só então faça o commit.
`tests/test_modelos.py` cobra o esqueleto.
