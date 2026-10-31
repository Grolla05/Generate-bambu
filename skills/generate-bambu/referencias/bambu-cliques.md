# Bambu Studio por cliques — plano B

Use só se `scripts/fatiar.py` falhar ou se não houver Python. O caminho normal é o
passo 4 do `SKILL.md`, sem clique nenhum.

Exige controle de tela. Sem ele, siga "Roteiro para o usuário", no fim.

---

## Abrir

Assuma sempre que está fechado. Interface em **inglês**.

Peça acesso ao Bambu Studio, abra o programa, espere ~5 s e **capture a tela**.

Ele demora e costuma abrir com algo na frente: update (*Later*), release notes
(*OK*), login (pode ignorar), ou seleção de impressora na primeira execução
(**Bambu Lab A1**). Feche o que estiver na frente e maximize a janela — botão
fora da área visível é a causa mais comum de clique que não acontece.

Controle de tela é frágil: **capture a tela antes de cada ação que muda
estado, e depois para confirmar que mudou.** Nunca encadeie três cliques às
cegas. Prefira atalho de teclado a clique.

Se tiver controle de tela e ainda assim não conseguir abrir, **diga que não
conseguiu** e siga o roteiro. Não descreva o que o programa faria.

---

## Carregar o .3mf do passo 3

`Ctrl+O` (File → Open Project). No diálogo do Windows **não navegue pelas
pastas**: clique no campo *File name*, digite o caminho completo e tecle `Enter`.
Se perguntar entre abrir como projeto ou importar geometria, escolha projeto.

**Dois diálogos aparecem, nesta ordem — testados:**

1. *Standard 3mf Import color* — o Bambu Studio leu as cores do arquivo e
   mostra a prévia já colorida e uma tabela *Matching* (cor → filamento).
   Capture a tela e confira: uma cor por slot, prévia com as cores certas. Se
   *Sync info* já trouxe os filamentos do AMS, use *Color match* para casar
   com os rolos carregados; senão o padrão *Append* cria um filamento novo
   por cor. Então *OK*.
2. *Multi-part object detected* ("objects positioned at multiple heights") —
   responda **Yes**, sempre. Com *No*, cada slot vira objeto separado e cai
   para a mesa: o relevo e o texto descolam da base.

O aviso laranja "The 3mf is not from Bambu Lab, load geometry data and color
data only" é normal: o perfil de impressão não vem nesse arquivo.

---

## Conferir

**Dimensões.** Selecione e leia o painel *Size*. Os números têm que bater com o
que o modelador mostrou. Peça 1000× menor ou maior é erro de unidade — volte ao
passo 3 e reexporte, **não conserte escalando aqui**.

**Altura de camada 0,12 mm.** No painel de processo à direita, escolha o perfil
de 0.12 mm (na A1 costuma aparecer como *0.12mm Fine*) ou abra as configurações e
ponha `0.12` em *Layer height*. Ponha `0.24` em *Initial layer height*, para as
alturas continuarem em múltiplos da camada. Capture a tela para confirmar.

**Filamentos.** A lista de objetos mostra um objeto com as partes `slot1`,
`slot2`… — todas com *Fila. 1*, e isso é normal: a cor vem pintada na malha, não
pela coluna. Confira na pré-visualização colorida que cada região está na cor
certa, e depois do slice que a lista de filamentos usados tem um por cor. O
número do filamento tem que ser o do rolo certo no AMS.

**Fatiar.** *Slice plate* ou `Ctrl+R`. Espere; capture a tela para confirmar — a
tela vira pré-visualização de camadas e o botão vira *Print plate*. Se falhar, o
motivo aparece em vermelho: objeto fora da área, malha não-manifold, ou nenhum
filamento configurado (PLA Basic serve de default).

**Quando travar.** Se um clique não produzir o efeito esperado, não repita —
capture a tela e leia (quase sempre há um diálogo na frente, ou a janela perdeu o
foco). Duas ou três tentativas, então pare, descreva o que está na tela e
pergunte. O usuário está na frente do computador.

Colete da tela o **tempo estimado** e as **gramas por filamento** e volte ao
passo 6. **Nunca clique em *Print plate* ou *Send*.**

---

## Roteiro para o usuário

Sem controle de tela, tudo que você disser sobre o Bambu Studio vem do que o
usuário informar.

1. Dê o caminho completo do `.3mf`.
2. Passe as instruções, nesta ordem: abrir com `Ctrl+O`; no diálogo de cor,
   conferir e dar *OK*; em *Multi-part object detected*, responder **Yes**;
   escolher o perfil de 0,12 mm; fatiar com `Ctrl+R`.
3. Peça os números: tamanho em X, Y e Z no painel *Size*, altura de camada, tempo
   estimado e gramas por filamento.
4. Compare o tamanho com o que o modelador mostrou. Se não bater, volte ao passo 3
   e reexporte, sem escalar no Bambu Studio.
5. Volte ao passo 6.
