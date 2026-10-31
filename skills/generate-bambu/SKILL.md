---
name: generate-bambu
description: "Modela peça para impressão 3D direto no Autodesk Fusion via MCP, numa sequência fixa: cria o design paramétrico no projeto Bubble Studio 3D, valida e mostra no Fusion, espera o OK, só então exporta o .3mf multicor (um objeto por slot do AMS, camada 0,12 mm), abre o Bambu Studio, carrega o projeto e pergunta antes de imprimir. Use em qualquer pedido de criar, desenhar, modelar ou projetar objeto para impressão 3D, placa, letreiro, chaveiro, lembrancinha, engrenagem, vaso, pote, suporte ou peça multicolor. Modelagem só pelo Fusion — sem SVG, sem Blender. Limite 250×250×250 mm (Bambu Lab A1)."
license: MIT
compatibility: "Windows; Autodesk Fusion com servidor MCP local ativo; Bambu Studio em inglês (testado na 02.08); Bambu Lab A1 com AMS Lite. Controle de tela é opcional."
metadata:
  author: Felipe Grolla
  version: "1.0.0"
---

# generate-bambu

Uma sequência fixa de seis passos, do Fusion à impressora. Não pule passo,
não troque a ordem, e não substitua o que cada passo entrega.

```
1. modelar no Fusion + validar + mostrar
2. esperar o OK do usuário
3. exportar o .3mf multicor, camada 0,12 mm
4. abrir o Bambu Studio
5. carregar o projeto e conferir
6. perguntar antes de imprimir
```

**Cinco regras que valem o fluxo inteiro:**

- **A modelagem é no Fusion, e só.** Toda geometria nasce por script no
  Fusion via `fusion_mcp_execute`. Nunca gere SVG, malha em Python, OpenSCAD
  ou CadQuery como substituto. Se o Fusion não responder, pare e peça para o
  usuário abri-lo (passo 0).
- **A saída é `.3mf`, e só.** Nunca ZIP, nunca STL, nunca OBJ, nunca uma pasta
  de arquivos. Um objeto por slot do AMS, dentro de um `.3mf` só.
- **A prévia é o design aberto no Fusion.** O usuário gira a peça lá, na tela
  dele. Seus screenshots servem para **você** conferir o que construiu antes
  de mostrar — não são a prévia, e nunca substituem o design aberto.
- **Nada de "de memória".** Se for falar do que está na tela do Fusion ou do
  Bambu Studio, tire o screenshot e leia. Se não conseguir, diga que não
  conseguiu.
- **O `.3mf` só nasce depois do OK.** O passo 1 modela e salva o design, mas
  não exporta arquivo de impressão nenhum.

Arquivos desta skill (leia sob demanda):

| Arquivo | Quando |
|---|---|
| `referencias/fusion-api.md` | sempre — receitas testadas de script, validação, cor, exportação |
| `helpers/agrupar_3mf.py` | passo 3 — cole inteiro no script de exportação |
| `referencias/fdm-a1.md` | ao decidir espessura, folga, orientação, balanço |
| `referencias/limites.md` | quando o pedido não couber no método |

---

## Passo 0 — Triagem

Antes de modelar qualquer coisa.

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
venda a linha é mais firme — a nota de Risco Jurídico do projeto trata disso.

**2. O pedido é geometria construída?** Placa, letreiro, chaveiro,
lembrancinha, ímã, porta-copo, quadro em relevo, engrenagem, vaso, pote,
suporte, caixa com tampa, peça com rosca ou encaixe: sim — o Fusion faz
booleana, fillet, chamfer, shell, rosca e texto. Rosto, corpo, animal
realista: **não** — diga na primeira resposta. Aqui, sim, uma versão
estilizada é boa saída, porque o assunto não é de ninguém: ofereça e, se o
usuário topar, **modele e mostre**.

**3. Quantas cores?** O AMS Lite tem 4 slots. Uma cor = um `slotN` = um
objeto no 3MF = um filamento. Acima de 2 cores, avise do custo de purga.

**4. O Fusion está respondendo?** `fusion_mcp_read` com
`{queryType: "document", operation: "open"}`. Se der erro ou não responder,
diga que o Fusion não está acessível e peça para o usuário abri-lo (ou abra
com `computer_open_application`, se tiver acesso). Não siga sem ele.

`referencias/limites.md` tem a triagem completa.

---

## Passo 1 — Modelar no Fusion, validar e mostrar

O passo mais longo, e o único que o usuário vê antes de decidir. Leia
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
- **Appearance `bubble_#rrggbb`** em todo corpo (receita em `fusion-api.md`).
  É ela que leva a cor para o 3MF.
- Texto vira um corpo por letra e não dá para unir: nomeie todas com o mesmo
  `slotN_` — o passo 3 junta.
- Termine o último script com `app.activeViewport.fit()`.

**1c. Validar.** Rode o script de validação de `fusion-api.md` com
`readOnly: true`. Precisa dar: todo corpo sólido e com prefixo `slotN_`;
alturas em múltiplos de camada; peça inteira em 250×250×250; no máximo 4
slots; **nenhuma interferência** entre corpos; nenhuma cor padrão do Fusion.
Qualquer falha é defeito de geometria, não opinião — conserte antes de
mostrar. Confira também espessuras mínimas e balanços contra `fdm-a1.md`.

**1d. Conferir com os olhos e salvar.** Screenshots `iso-top-right`, `front`
e `top` com `fusion_mcp_read` (`queryType: "screenshot"`). Olhe de verdade:
o relevo está em cima da base, o texto legível e no lugar, o furo onde
deveria? Se algo destoar do pedido, conserte e tire de novo. Então salve o
documento no projeto **Bubble Studio 3D** com o nome da peça em duas a quatro
palavras — nunca "Peça" ou "Teste" (o código cria o projeto se faltar).

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

**Se pedir ajuste:** mude os *User Parameters* (`expression`) quando o ajuste
for de medida, ou rode um script de correção; `fusion_mcp_update → undo`
desfaz o último script. Sempre no **mesmo documento**: valide de novo (1c),
confira (1d) e salve como nova versão (`save`), para o histórico ficar numa
peça só. Quantas voltas forem necessárias.

**Se o usuário mandar pular a revisão:** pule, é a peça dele. Mas valide e
diga as dimensões numa linha — custa segundos.

---

## Passo 3 — Exportar o .3mf

Só agora, e só com o OK na mão.

Um script que: exporta o componente raiz em 3MF com
`MeshRefinementHigh` para um arquivo temporário; passa por
`agrupar_por_slot()` (cole `helpers/agrupar_3mf.py` inteiro no começo do
script) gravando o final em `D:/Bambu Lab/projeto/<nome-da-peca>.3mf`; apaga o
temporário; imprime o relatório. Receita pronta em `fusion-api.md`.

Do mesmo design que ele aprovou, sem remodelar nada — remodelar abriria
espaço para o arquivo divergir do que foi aprovado.

**Confira o relatório:** um objeto por slot, `tudo_fechado: true`, cor certa
em cada slot, `avisos` vazio, e o volume de cada slot batendo com a soma dos
volumes dos corpos na validação (diferença acima de 1 % é sinal de corpo
perdido). Se `agrupar_por_slot` recusar (corpo sem `slotN_`, mais de 4 slots,
unidade errada), corrija no Fusion e exporte de novo.

Um arquivo. Nada de ZIP, nada de pasta com várias peças soltas, nada de STL.

---

## Passo 4 — Abrir o Bambu Studio

Assuma sempre que está fechado. Interface em **inglês**.

`computer_request_access` → Bambu Studio; `computer_open_application`;
`computer_wait` ~5 s; **screenshot**.

Ele demora e costuma abrir com algo na frente: update (*Later*), release notes
(*OK*), login (pode ignorar), ou seleção de impressora na primeira execução
(**Bambu Lab A1**). Feche o que estiver na frente e maximize a janela — botão
fora da área visível é a causa mais comum de clique que não acontece.

Controle por screenshot é frágil: **screenshot antes de cada ação que muda
estado, e depois para confirmar que mudou.** Nunca encadeie três cliques às
cegas. Prefira atalho de teclado a clique.

Se não conseguir abrir, **diga que não conseguiu** e pare. Não descreva o que
o programa faria.

---

## Passo 5 — Carregar o projeto e conferir

**Carregar.** `Ctrl+O` (File → Open Project). No diálogo do Windows **não
navegue pelas pastas**: clique no campo *File name*, digite o caminho completo
com `computer_type` e `Enter`. O espaço em `D:\Bambu Lab` não precisa de
aspas. Se perguntar entre abrir como projeto ou importar geometria, escolha
projeto.

**Dois diálogos aparecem, nesta ordem — testados:**

1. *Standard 3mf Import color* — o Bambu Studio leu as cores do arquivo e
   mostra a prévia já colorida e uma tabela *Matching* (cor → filamento).
   Screenshot e confira: uma cor por slot, prévia com as cores certas. Se
   *Sync info* já trouxe os filamentos do AMS, use *Color match* para casar
   com os rolos carregados; senão o padrão *Append* cria um filamento novo
   por cor. Então *OK*.
2. *Multi-part object detected* ("objects positioned at multiple heights") —
   responda **Yes**, sempre. Com *No*, cada slot vira objeto separado e cai
   para a mesa: o relevo e o texto descolam da base.

O aviso laranja "The 3mf is not from Bambu Lab, load geometry data and color
data only" é normal: o perfil de impressão não vem no arquivo.

**Conferir as dimensões — não pule.** Selecione e leia o painel *Size*. Os
números têm que bater com o que o Fusion mostrou. Peça 1000× menor ou maior é
erro de unidade — volte ao passo 3 e reexporte, **não conserte escalando
aqui**: o erro volta na próxima peça.

**Altura de camada 0,12 mm.** No painel de processo à direita, escolha o
perfil de 0.12 mm (na A1 costuma aparecer como *0.12mm Fine*) ou abra as
configurações e ponha `0.12` em *Layer height*. Screenshot para confirmar que
pegou. Isto não vem no arquivo: o 3MF carrega geometria e cor, não o perfil de
impressão.

**Conferir os filamentos.** A lista de objetos mostra um objeto com as
partes `slot1`, `slot2`… — todas com *Fila. 1*, e isso é normal: a cor vem
pintada na malha, não pela coluna. Quem manda é a pintura e a tabela do
diálogo de cor. Confira na pré-visualização colorida que cada região está na
cor certa, e depois do slice que a lista de filamentos usados tem um por cor.
O número do filamento tem que ser o do rolo certo no AMS — quem decide o slot
é o Bambu Studio, não o arquivo.

**Fatiar.** *Slice plate* ou `Ctrl+R`. Espere; screenshot para confirmar — a
tela vira pré-visualização de camadas e o botão vira *Print plate*. Se falhar,
o motivo aparece em vermelho: objeto fora da área, malha não-manifold, ou
nenhum filamento configurado (PLA Basic serve de default). Malha não-manifold
não deveria chegar aqui — os passos 1 e 3 pegam isso.

**Quando travar.** Se um clique não produzir o efeito esperado, não repita —
tire screenshot e leia a tela (quase sempre há um diálogo na frente, ou a
janela perdeu o foco). Duas ou três tentativas, então pare, descreva o que
está na tela e pergunte. O usuário está na frente do computador.

---

## Passo 6 — Perguntar antes de imprimir

Depois do slice, colete da tela o **tempo estimado** e o **consumo em gramas**
(por filamento, em peça multicor). Confirme que a altura de camada ficou em
0,12 mm.

Então pergunte: **posso mandar imprimir?**

**Pare aqui.** Não clique em *Print plate* → *Send*, nem em *Send and print*,
sem a resposta. A peça vira plástico e tempo de máquina a partir desse clique.

---

## Depois: registrar no vault

Com tempo e gramas na mão — os dois números que só existem depois de fatiar —
acrescente uma linha em `🚀 Projetos/Empresa impressora 3D/Catálogo/Catálogo
Inicial.md`, na seção **"🛠️ Peças autorais"**. Se não existir, crie antes da
seção "🔗 Conexões no Vault":

```markdown
## 🛠️ Peças autorais

Peças desenhadas internamente. Licença própria — **venda liberada, sem
dependência de autorização de criador** (ver o bloqueio de licença da tabela acima).

| ID | Peça | Medidas (mm) | Cores | Peso (g) | Tempo (h) | Arquivo | Data |
|---|---|---|---|---|---|---|---|
```

IDs autorais usam prefixo **A** (A01, A02…) para não colidir com os P## da
planilha da MakerWorld. Em *Arquivo*, ponha o `.3mf` e o nome do documento no
Fusion. Leia com `obsidian_get_file_contents`, continue a numeração, e insira
com `obsidian_patch_content` — não reescreva a nota.

Na primeira peça registrada, vale dizer o gancho: a nota documenta que 8 dos
11 produtos do catálogo religioso estão travados por licença de terceiros.
Peça autoral não tem esse problema — é a saída do gargalo que a nota aponta.

**Licença do Fusion.** A licença atual é Education (uso não comercial), e o
usuário modela no Fusion para uso próprio e presentes. Se a peça registrada
for para **venda**, lembre em uma linha que a licença do Fusion precisa ser
revista antes.

---

## Operações comuns

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
valide, confira, salve o design no Fusion, deixe tudo pronto com a mensagem de
validação. Não exporte o `.3mf`, não abra o Bambu Studio, não imprima.
