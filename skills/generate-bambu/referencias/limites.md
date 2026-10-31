# Limites — o que este método não faz, e o que fazer então

Leia quando o pedido não couber nas operações do Fusion por script. Forma orgânica
de ninguém vai para o Blender (caso B).

---

## O que entra

| Peça | Como no Fusion |
|---|---|
| Placa, letreiro, chaveiro, ímã, marcador, etiqueta | sketch + extrusão |
| Lembrancinha plana personalizada, em lote na mesma mesa | extrusão + padrão retangular (`rectangularPatternFeatures`) |
| Quadro/brasão em relevo por camadas, multicor | uma extrusão por cor, em planos `N * camada` |
| Texto em relevo ou gravado | `sketchTexts` + extrusão ou corte |
| Porta-copo, base, stencil, gabarito | extrusão + corte |
| Engrenagem de dentes retos | perfil evolvente no sketch (spline por pontos) + extrusão + padrão circular |
| Vaso, pote, cúpula, anel, polia, bocal | `revolveFeatures` |
| Caixa, estojo, copo, organizador | extrusão + `shellFeatures` |
| Bordas arredondadas e chanfros | `filletFeatures`, `chamferFeatures` |
| Rosca, parafuso, porca | `threadFeatures` (modelada, com folga de 0,3 mm) |
| Encaixe 3D, rabo de andorinha, tampa que encaixa | booleanas com o parâmetro `folga` |
| Alça, gancho, calha curva | `sweepFeatures` ao longo de um caminho |
| Transição entre seções (funil, bico) | `loftFeatures` |

## O que não entra

| Peça | Por quê | Saída |
|---|---|---|
| Rosto, corpo, animal realista, estátua | forma arbitrária: não existe fórmula | caso B abaixo |
| Carro de marca, personagem, mascote, logo de time | design de terceiro — e estilizar não resolve | caso A abaixo |
| Mais cores que `maquina.slots` | são 4 slots no AMS e no AMS Lite | reduzir paleta, ou pintar à mão no acabamento |
| Peça maior que `maquina.limite_mm` | não cabe na mesa (250 mm na A1 e P1S, 175 mm na A1 mini) | partir em módulos (`fdm-a1.md`) |
| Malha pronta (STL baixado) para remodelar | o fluxo modela do zero | importar só como referência visual; licença conferida antes |

---

## Os dois eixos que as pessoas confundem

"Complexo" não é uma coisa só.

**Complexidade matemática** — um flanco evolvente, um padrão radial de 200
elementos, um lattice. Parece impossível e sai de trinta linhas de script no Fusion, exato.
Código humilha desenho manual aqui.

**Arbitrariedade de forma** — uma Porsche 911, uma action figure, um rosto.
Parece "só uma casca" e é intratável, porque não existe fórmula: o que define
aquela carroceria é continuidade de curvatura entre painéis e linhas de
caráter que alguém desenhou olhando o reflexo. É disciplina própria na
indústria, meses de trabalho.

**O que trava é o segundo eixo, não o primeiro.** Diga isso nesses termos — é
a explicação que responde "por que não dá um carro, se dá uma engrenagem?".

---

## Quando a resposta é "não desenho isso"

Diga na **primeira resposta**, antes de gerar nada. Mas a saída certa depende
de **por que** não dá — e são dois motivos bem diferentes, que pedem respostas
opostas.

### Caso A — o assunto é de outra pessoa

Carro de marca (GT-R, Fusca, Porsche), personagem de anime, herói, mascote,
logo de time, boneco de filme.

**A armadilha: versão estilizada NÃO é a saída aqui.** Um GT-R R34 em silhueta
de camadas continua sendo o design da Nissan; um Pikachu low-poly continua
sendo o Pikachu. Estilizar muda a aparência, não a autoria. Oferecer "faço uma
versão estilizada" nesse caso é oferecer o mesmo problema com outra roupa — e
pior, com a aparência de ter resolvido.

Ofereça, nesta ordem:

1. **Desenho original seu.** Um carro esportivo inventado, um motivo genérico
   que não seja um modelo específico, uma peça que evoque o tema sem ser a
   coisa. Isto sim é saída, e é autoral: pode ser vendida sem depender de
   autorização de ninguém.
2. **Modelo pronto com a licença conferida** (MakerWorld, Printables). Boa
   parte tem licença não comercial, o que serve para uso próprio e não para
   venda. Aqui você é útil de verdade: não desenhar, mas **preparar** —
   conferir escala, reorientar, ver se cabe na A1 — e **ler a licença antes**.
3. **Licenciar**, se o item for virar produto de verdade. Fora do seu alcance,
   mas é a resposta honesta quando o volume justifica.

Diga isso em uma linha, sem sermão, e siga. Em contexto de venda a linha é
mais firme que em contexto de uso próprio, e vale nomear a diferença.

### Caso B — a forma é arbitrária, mas de ninguém

Rosto genérico, corpo, animal realista, estátua, bicho inventado com anatomia.

Aqui **a versão estilizada é a saída boa** — e é o forte deste fluxo. Ofereça,
nesta ordem:

1. **Versão estilizada ou geométrica no Blender** (`blender-api.md`): low-poly,
   chibi, volumes simples. Sem Blender, silhueta plana em camadas de cor no Fusion.
   Costuma ser exatamente o que a pessoa queria. Se ela topar, **gere e mostre**
   com medidas sensatas em vez de perguntar detalhe — é mais rápido ajustar vendo.
2. **IA imagem→3D** (Tripo, Meshy, Hunyuan3D) para estilizado. Para
   hard-surface de precisão a malha sai mole e ondulada.
3. **Escultura manual**, pelo usuário, em Blender ou ZBrush.

Forma orgânica no Fusion existe (T-Splines, ambiente *Form*), mas não se
dirige bem por script. E realismo não se resolve por código em programa nenhum:
não proponha esculpir rosto fiel, nem no Blender.

Casos mistos existem — um porta-vela com relevo simples, um letreiro com
silhueta. Se a parte orgânica é decorativa e secundária, siga; avise que sairá
simplificada.

---

## Quando o modelador não está disponível

Se o modelador escolhido não responder, diga isso e peça para o usuário abri-lo.
Peça de medida exata sem Fusion: pare, porque malha no Blender não tem parâmetros, e
não troque em silêncio. Nunca gere SVG, malha solta em Python, OpenSCAD ou CadQuery
no lugar.

---

Imprimir para si é uma coisa; vender é outra. Nomeie a diferença quando o contexto for
comercial: uma linha basta.
