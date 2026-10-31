---
name: generate-bambu
description: "Modela e prepara peças para impressão 3D multicor no Autodesk Fusion ou no Blender, com fatiamento no Bambu Studio. Use para criar, desenhar, projetar ou modelar placa, letreiro, chaveiro, lembrancinha, ímã, porta-copo, vaso, pote, caixa, suporte, engrenagem, bicho, boneco low-poly ou peça multicolor. Use for 3D print, 3D model, keychain, nameplate, sign, coaster, vase, box, bracket, gear, multicolor, 3MF, Bambu Lab, AMS, Fusion. Não use para SVG ou desenho 2D que não vá para impressão 3D."
license: MIT
compatibility: "Windows; Python 3.10+; Autodesk Fusion com servidor MCP local ativo ou Blender 5.1+; Bambu Studio testado na 02.08.03.66; Bambu Lab A1 com AMS Lite (A1 mini e P1S conferidas até o fatiamento). Controle de tela é opcional."
metadata:
  author: Felipe Grolla
  version: "3.1.0"
---

# generate-bambu

Uma sequência fixa de seis passos, do modelador à impressora. Não pule passo,
não troque a ordem, e não substitua o que cada passo entrega.

```
1. modelar no Fusion ou no Blender + validar + mostrar
2. esperar o OK do usuário
3. exportar o .3mf multicor, camada 0,12 mm
4. fatiar por script
5. abrir no Bambu Studio e conferir
6. perguntar antes de imprimir
```

**Seis regras que valem o fluxo inteiro:**

- **Um modelador por peça, escolhido no passo 0.** Toda geometria nasce por
  script: no Fusion via `fusion_mcp_execute`, ou no Blender. Medida exata é
  sempre Fusion. Nunca gere SVG, OpenSCAD, CadQuery ou malha solta em Python como
  substituto, e não troque de modelador em silêncio se o escolhido não responder.
- **A saída é `.3mf`, e só.** Nunca ZIP, nunca STL, nunca OBJ. São dois
  arquivos: o `.3mf` da peça, com um objeto por slot do AMS, e o fatiado que
  sai dele em `_fatiados/`.
- **A prévia é a peça aberta no modelador.** O usuário gira a peça lá, na tela
  dele. Seus screenshots servem para **você** conferir o que construiu antes
  de mostrar — não são a prévia, e nunca substituem o arquivo aberto.
- **Nada de "de memória".** Se for falar do que está na tela do modelador ou do
  Bambu Studio, capture a tela e leia. Se não conseguir, diga isso e peça o
  dado ao usuário. Nunca presuma.
- **O `.3mf` só nasce depois do OK.** O passo 1 modela e salva o design, mas
  não exporta arquivo de impressão nenhum.
- **Você nunca imprime.** Nenhum script desta skill envia peça para a
  impressora. Quem clica em *Print plate* é o usuário, sempre. Controle de tela
  não clica nesse botão nem em *Send*, nem depois de um "sim".

Arquivos desta skill (leia sob demanda):

| Arquivo | Quando |
|---|---|
| `referencias/fusion-api.md` | peça no Fusion — receitas testadas de script, validação, cor, exportação |
| `referencias/blender-api.md` | peça no Blender — receitas testadas |
| `helpers/blender_3mf.py` | peça no Blender — importe no script |
| `scripts/detectar_modeladores.py` | passo 0 — qual modelador usar |
| `scripts/agrupar.py` | passo 3 — um objeto por slot, a partir do bruto do Fusion |
| `helpers/agrupar_3mf.py` | passo 3 sem terminal — o Fusion importa este arquivo |
| `scripts/diagnostico.py` | passo 0 — o que está pronto nesta máquina |
| `scripts/fatiar.py` | passo 4 — fatia sem clique e devolve tempo e gramas |
| `scripts/status.py` | passo 6 e depois — só leitura, e só se o usuário pedir |
| `scripts/registro.py` | depois do passo 6 — linha pronta para levar a uma nota |
| `scripts/config.py` | pasta de saída, Bambu Studio, máquina, projeto do Fusion |
| `referencias/bambu-cliques.md` | plano B, se o passo 4 falhar |
| `referencias/fdm-a1.md` | ao decidir espessura, folga, orientação, balanço |
| `referencias/limites.md` | quando o pedido não couber no método |
| `referencias/agentes.md` | para traduzir uma capacidade na ferramenta do seu agente, ou ligar o MCP do Fusion |

---

## Passo 0 — Triagem

Antes de modelar qualquer coisa. Se `~/.generate-bambu/perfil.md` existir, leia: ele
traz o contexto de quem usa (para que servem as peças, licenças, onde registrar). O
perfil acrescenta contexto e nunca afrouxa as regras acima nem as paradas dos passos
2 e 6.

**1. O assunto é de outra pessoa?** Carro de marca, personagem de anime,
herói, logo de time, mascote, boneco de filme: o desenho é **design de
terceiro**.

Tem uma armadilha aqui: uma versão "estilizada" de um design de marca
**continua sendo o design dele**. Mudar pose, cor ou nível de detalhe não cria
originalidade. Não ofereça modelar uma versão estilizada de um GT-R, de um
Porsche ou de um personagem — não é saída, é o mesmo problema com outra roupa.

O que dá para oferecer: um desenho **original** seu (um carro inventado, um
motivo genérico que não seja um modelo específico), ou um **modelo pronto com
licença conferida**. Diga em uma linha, sem sermão, e siga. Em contexto de
venda a linha é mais firme.

**2. O pedido é geometria construída?** Placa, letreiro, chaveiro,
lembrancinha, ímã, porta-copo, quadro em relevo, engrenagem, vaso, pote,
suporte, caixa com tampa, peça com rosca ou encaixe: sim — o Fusion faz
booleana, fillet, chamfer, shell, rosca e texto. Bicho, boneco e forma orgânica
de ninguém: versão estilizada ou low-poly no Blender. Realismo, não — diga na
primeira resposta e ofereça a versão estilizada: se o usuário topar, **modele e
mostre**.

**3. Quantas cores?** O limite é `maquina.slots`: 4 no AMS e no AMS Lite. Uma cor
= um `slotN` = um objeto no 3MF = um filamento. Acima de 2 cores, avise do custo de
purga.

**4. Cabe na mesa?** O limite é `maquina.limite_mm` nos três eixos: 250 mm na A1 e na
P1S, 175 mm na A1 mini. Peça maior: diga na primeira resposta e proponha dividir ou
reduzir.

**5. Qual modelador?** Rode `python scripts/detectar_modeladores.py --tipo
preciso|organico|qualquer`. Preciso é medida exata, rosca, encaixe ou texto;
orgânico é o estilizado do item 2; qualquer é o que serve nos dois. Siga
`escolha.modelador` e diga em uma linha qual foi e por quê. Se `perguntar` vier
`true`, pergunte uma vez e grave em `modelador.preferido`. Sem modelador e sem
pergunta, passe o `motivo` e pare.

**6. O modelador responde?** No Fusion, rode `python scripts/diagnostico.py`. Se
`fusion.estado` for `respondendo`, siga. Nos outros casos, passe a `instrucao`
que ele devolve. Não siga sem ele. No Blender, veja `referencias/blender-api.md`:
com MCP, `get_objects_summary` prova a conexão; sem MCP, o script roda por
terminal.

Sem terminal, teste o Fusion com `fusion_mcp_read`, `{queryType: "document", operation:
"open"}`. Se der erro, peça para o usuário abrir o Fusion e ligar Preferences →
General → API → Fusion MCP Server, com *Apply* e depois *OK*.

**7. Para onde vai o arquivo?** Se `pasta_saida.caminho` vier vazio, pergunte
qual pasta usar e grave com `python scripts/config.py definir pasta_saida
"<pasta>"`.

**8. Qual impressora?** O `diagnostico.py` mostra `maquina`. Para trocar, `python
scripts/config.py maquina "A1 mini"` (ou `A1`, `P1S`). Se `impressao_testada` vier
`false`, diga em uma linha que esse modelo foi conferido até o fatiamento, nunca
impresso.

`referencias/limites.md` tem a triagem completa.

---

## Passo 1 — Modelar, validar e mostrar

O passo mais longo, e o único que o usuário vê antes de decidir. **No Blender,
siga `referencias/blender-api.md` em vez de 1a a 1d:** script com parâmetros no
topo, mesmo contrato de corpos, `validar()` e o `.blend` salvo na pasta de saída
para o usuário abrir. Depois, 1e vale igual. O resto deste passo é do Fusion: leia
`referencias/fusion-api.md` antes do primeiro script.

**1a. Documento novo.** Um documento por peça: design **paramétrico**,
unidade de exibição **mm**. Crie os *User Parameters* antes da geometria:
`camada = 0.12 mm` e todas as alturas como múltiplos dela (`base = 17 *
camada`, `relevo = 7 * camada`), mais `folga` quando houver encaixe.

**Sobre a camada de 0,12 mm.** O padrão desta skill. Toda altura que o usuário
pedir vira o múltiplo de 0,12 mais próximo — 0,8 mm vira `7 * camada` = 0,84
mm, porque o slicer não sabe fazer 0,8. Diga cada ajuste na mensagem: o
usuário aprova a peça que vai sair, não a que foi pedida.

**1b. Modelar por script.** `fusion_mcp_execute` com `featureType: "script"`;
o código precisa definir `run(context)`, e a API trabalha em **centímetro**.
Prefira scripts curtos, um por etapa (base, relevo, texto, acabamento), para
que um `undo` desfaça só a última.

Contrato de corpos — é dele que o resto do fluxo depende:

- **Cada cor é um corpo separado** (`NewBodyFeatureOperation`). Nunca `Join`
  entre cores.
- **Nome `slotN_descricao`** (`slot1_base`, `slot2_detalhe`, `slot3_texto_4`).
  O N é o slot do AMS; todos os corpos do mesmo slot têm a mesma cor.
- **Appearance `cor_#rrggbb`** em todo corpo (receita em `fusion-api.md`).
  É ela que leva a cor para o 3MF.
- Texto vira um corpo por letra e não dá para unir: nomeie todas com o mesmo
  `slotN_` — o passo 3 junta.
- Termine o último script com `app.activeViewport.fit()`.

**1c. Validar.** Rode o script de validação de `fusion-api.md` com
`readOnly: true`. Precisa dar `ok: true`. Ele cobra: todo corpo sólido e com
prefixo `slotN_`; alturas em múltiplos de camada; peça inteira dentro do limite da
máquina; slots dentro de `maquina.slots`, com uma cor por slot; **nenhuma
interferência** entre corpos;
nenhuma cor padrão do Fusion. Qualquer item em `erros` é defeito de geometria, não
opinião — conserte antes de mostrar. Confira também espessuras mínimas e balanços
contra `fdm-a1.md`.

**1d. Conferir com os olhos e salvar.** Screenshots `iso-top-right`, `front`
e `top` com `fusion_mcp_read` (`queryType: "screenshot"`). Olhe de verdade:
o relevo está em cima da base, o texto legível e no lugar, o furo onde
deveria? Se algo destoar do pedido, conserte e tire de novo. Se o seu agente
não enxergar a imagem que o MCP devolve, diga isso e peça para o usuário
conferir esses pontos no Fusion. Então salve o documento no projeto de
`fusion.projeto`, com o nome da peça em duas a quatro palavras — nunca "Peça" ou
"Teste" (o código cria o projeto se faltar).

**1e. Escreva o texto curto:** diga que a peça está aberta no Fusion para ele
girar e inspecionar; o que é em uma frase; **dimensões finais em mm** nos três
eixos; cada slot com cor, altura e número de camadas; os ajustes de camada que
houve; e os avisos que importam.

---

## Passo 2 — Esperar o OK

**Pare aqui.** Pergunte diretamente se está aprovado ou o que mudar.

"Ficou bom", "pode ir", "aprovado" contam. Silêncio não conta. A validação ter
passado também não conta — ela diz que a geometria é válida, não que a peça
ficou boa. Quem aprova a forma é quem vai usar ou vender a peça.

**Se pedir ajuste no Blender:** mude os parâmetros no topo do script e rode de
novo, do começo. No Fusion, mude os *User Parameters* (`expression`) quando o ajuste
for de medida, ou rode um script de correção; `fusion_mcp_update → undo`
desfaz o último script. Sempre no **mesmo documento**: valide de novo (1c),
confira (1d) e salve como nova versão (`save`), para o histórico ficar numa
peça só. Quantas voltas forem necessárias.

**Se o usuário mandar pular a revisão:** pule, é a peça dele. Mas valide e
diga as dimensões numa linha — custa segundos.

---

## Passo 3 — Exportar o .3mf

Só agora, e só com o OK na mão.

**No Blender:** `b.exportar(...)`, de `referencias/blender-api.md`. **No Fusion:**
um script exporta o componente raiz em 3MF com `MeshRefinementHigh` para
`<pasta_saida>/.<nome-da-peca>.bruto.3mf` e imprime o caminho. Depois:

```
python scripts/agrupar.py "<bruto>" "<pasta_saida>/<nome-da-peca>.3mf" --apagar-bruto
```

Sem terminal, o script do Fusion importa `helpers/agrupar_3mf.py` pela pasta da
skill. Colar o helper inteiro é o último recurso. Receitas em `fusion-api.md`.

Do mesmo design que ele aprovou, sem remodelar nada — remodelar abriria
espaço para o arquivo divergir do que foi aprovado.

**Confira o relatório:** um objeto por slot, `tudo_fechado: true`, cor certa
em cada slot, `avisos` vazio, e o volume de cada slot batendo com a soma dos
volumes dos corpos na validação (diferença acima de 1 % é sinal de corpo
perdido). Se o agrupamento recusar (corpo sem `slotN_`, slot fora do limite, duas
cores num slot, unidade errada), corrija no Fusion e exporte de novo.

Um arquivo. Nada de ZIP, nada de pasta com várias peças soltas, nada de STL.

---

## Passo 4 — Fatiar por script

```
python scripts/fatiar.py "<pasta_saida>/<nome-da-peca>.3mf" --abrir --modelador fusion --documento "<nome no modelador>"
```

Sem clique e sem diálogo. O script monta um projeto nativo do Bambu Studio com
os perfis da configuração (0,12 mm, e primeira camada de 0,24 mm para as alturas
seguirem múltiplos da camada), fatia, grava em
`<pasta_saida>/_fatiados/<nome-da-peca>/<nome-da-peca>.gcode.3mf` e anota a peça no
registro local. Ele não fala com a impressora.

O JSON traz `tempo_s`, `peso_g`, `camadas`, `camada_mm`, `dimensoes_mm`,
`filamentos` e `avisos`. Compare `dimensoes_mm` com o que o modelador mostrou. Se o
script achar divergência de camada, de filamentos ou de dimensões, ele sai com
erro, e o erro é real: corrija a causa.

Peça multicor deixa lugar para a torre de purga no canto da mesa. Se ela ocupar
quase a mesa inteira nos dois lados, o script recusa e diz até quanto reduzir:
proponha reduzir um lado ou usar uma cor.

| Código | Quer dizer | O que fazer |
|---|---|---|
| 2 | entrada inválida, ou peça não cabe | corrija e exporte de novo |
| 3 | Bambu Studio recusou | leia `erro`; se não resolver, siga o plano B |
| 4 | Bambu Studio não encontrado | peça o caminho e grave em `bambu_studio.exe` |

**Plano B:** `referencias/bambu-cliques.md`, se o script falhar ou não houver
Python. Nunca invente tempo ou gramas.

---

## Passo 5 — Abrir e conferir

O `--abrir` mostra o fatiado no Bambu Studio. Ele abre direto na pré-visualização,
sem diálogo, com a peça colorida, o perfil de 0,12 mm e o botão *Print plate*.

Diga para o usuário conferir ali as cores, o relevo em cima da base e os rolos
carregados. Não afirme o que está na tela sem ver: sem captura de tela, pergunte.

**Sobre os rolos.** Cada `slotN` deveria estar na bandeja N do AMS, mas quem casa
filamento com bandeja é a janela de envio do Bambu Studio. Se o usuário quiser,
`python scripts/status.py --conferir <fatiado>` compara os slots com o que a A1
informa. Use só com pedido dele: é leitura, mas fala com a impressora.

---

## Passo 6 — Perguntar antes de imprimir

Mostre **tempo estimado**, **gramas por filamento** e confirme a camada de 0,12 mm.

Então diga que está pronto e que imprimir é com ele: **clicar em *Print plate* no
Bambu Studio**.

**Pare aqui.** Não há comando nesta skill que envie a peça, e controle de tela não
clica em *Print plate* nem em *Send*. Nunca diga que a peça foi enviada. A peça
vira plástico e tempo de máquina a partir desse clique.

---

## Depois: registrar

O `fatiar.py` já anotou a peça em `~/.generate-bambu/registro.jsonl`, e o relatório
traz `registro.id`. Refatiar mantém o mesmo id. Quem fatiou à mão pelo plano B anota com
`python scripts/registro.py adicionar <fatiado>`.

Para levar a peça a uma nota, rode `python scripts/registro.py linha`, que devolve a
linha Markdown, `nota` e `secao`. Com `nota` preenchida e acesso a notas, insira só essa
linha na seção, sem reescrever a nota. Sem `nota`, ou sem acesso, entregue a linha pronta
para o usuário colar. O perfil pode dizer mais sobre esse destino.

Tempo e gramas só vêm do fatiado. Nunca digite esses números.

**Licença do modelador.** Se a peça for para **venda** e o Fusion estiver numa licença
não comercial, lembre em uma linha que a licença precisa ser revista antes. O Blender
não tem essa trava.

---

## Operações comuns no Fusion

| Peça | Como no Fusion |
|---|---|
| Placa, letreiro, chaveiro, ímã, porta-copo | sketch + extrusão; relevo de cor como corpo novo num plano deslocado |
| Quadro/brasão em camadas | uma extrusão por cor, cada uma num plano `N * camada` acima |
| Texto | `sketchTexts` + extrusão; uma letra por corpo, mesmo `slotN_` |
| Vaso, pote, cúpula, anel | `revolveFeatures` com o perfil da parede (no plano XZ, Y do sketch = −Z) |
| Caixa, copo, estojo | extrusão + `shellFeatures` |
| Bordas | `filletFeatures`; chanfro de 0,5–1 mm na base contra empenamento |
| Rosca, encaixe | `threadFeatures`, booleana com `folga` (`fdm-a1.md`) |

Receitas de cada uma em `referencias/fusion-api.md`.

---

## Calibração — uma vez, antes de confiar nas medidas

A placa de calibração está descrita no fim de `fusion-api.md`: modele no
Fusion e siga a sequência normal (~12 g, ~40 min). O desvio sistemático que
sobrar nos furos é a **folga de processo** da máquina: grave no parâmetro
`folga` das peças seguintes.

---

## Se o usuário não estiver acompanhando

O passo 2 é parada obrigatória. Se ele não responder, pare ali: modele,
valide, confira, salve a peça no modelador, deixe tudo pronto com a mensagem de
validação. Não exporte o `.3mf`, não fatie, não abra o Bambu Studio.
