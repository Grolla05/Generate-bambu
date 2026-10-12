# Regras FDM para a Bambu Lab A1

Consulta. Não precisa ler inteiro — pule para a seção que a peça exige.

Bico 0,4 mm · camada 0,12 mm (padrão da skill) · mesa 256×256×256 mm (use 250 como limite) ·
AMS Lite até 4 cores · até 500 mm/s.

O que mais diferencia a A1 das outras: **a mesa se move no eixo Y**. Peça alta
e estreita balança, e é o motivo de metade dos avisos deste arquivo.

Estas regras mudam **decisões de geometria**. Não são checklist de fim.

---

## Espessuras

| Elemento | Mínimo | Confortável | Sob esforço |
|---|---|---|---|
| Parede vertical | 0,8 mm (2 perímetros) | **1,2–1,6 mm** | 2,4 mm |
| Piso / teto | 0,8 mm | 1,2 mm | 2,0 mm |
| Pino, haste | — | 2,0 mm | 3,0 mm |
| Nervura | 0,8 mm | 1,2 mm | — |

Texto em relevo: 0,84 mm de altura (`7 * camada`), fonte ≥ 6 mm. Gravado: 0,6 mm de
profundidade, fonte ≥ 8 mm (gravado perdoa menos que relevo).

**Abaixo de 0,8 mm o slicer ignora a geometria — ela some sem aviso.** Use
1,2 mm como default quando o usuário não especificar. Em peça plana, a
"parede" é a espessura da camada de cor: 0,6 mm é o piso prático (5 camadas
a 0,12 mm: `5 * camada`).

---

## Precisão dimensional: dois erros diferentes

Confundir os dois é a causa de encaixe que não fecha. São independentes e se
somam.

**1. Erro de discretização (malha).** O Fusion modela círculo exato; quem
discretiza é a exportação. Com `MeshRefinementHigh` o desvio fica em ~0,014 mm
(um furo de Ø20 sai com ~190 lados) — abaixo do que a A1 resolve. Na prática
esse erro sumiu deste fluxo: **não compense furo por polígono inscrito.** Se
alguém exportar em refinamento baixo, ele volta (um Ø20 com 16 lados perde
0,38 mm no diâmetro).

**2. Folga de processo (impressora).** Plástico encolhe e o bico engorda a
parede para dentro. Não tem fórmula — mede-se. Por lado:

| Encaixe | Folga |
|---|---|
| Deslizante (corre livre) | 0,4 mm |
| **Justo (padrão)** | **0,2 mm** |
| Pressão / snap-fit | 0,1 mm |
| Rosca | 0,3 mm |
| Inserto (porca, ímã) | 0,1–0,2 mm |

Imprima a placa de calibração (fim de `fusion-api.md`) uma vez para medir a
folga real da sua máquina. Depois disso, grave o número no parâmetro `folga`.

Furo circular impresso ainda sai um pouco menor que o modelado — para
parafuso, acrescente 0,2–0,3 mm no diâmetro por cima da folga.

---

## Balanços

Ângulo medido **a partir da vertical**: parede vertical = 0°, teto plano = 90°.

- Até **45°**: imprime limpo, sem suporte. Projete para caber aqui.
- 45–60°: sai, mais feio embaixo.
- Acima de 60°: precisa suporte, que deixa marca e vai precisar de lixa.
- Vão horizontal (ponte) até ~20 mm a A1 resolve.

Peça feita só de extrusão tem parede vertical: **balanço não existe**, e
é uma das razões de este fluxo ser confiável. O assunto aparece em
revolução, loft, chanfro de topo e fillet grande, onde o perfil pode abrir demais — um vaso que alarga mais de 45°
em relação à vertical vai precisar de suporte. Feche o perfil dentro disso.

Furo horizontal sai ovalizado no topo. Se for funcional: deixe o eixo
vertical, ou modele como gota (teto em V a 45°).

---

## Aderência e empenamento

A peça gruda pela área da primeira camada, e na A1 o movimento da mesa agrava.

- Base menor que ~15×15 mm: sugira brim.
- **Canto vivo na base levanta.** Um chanfro de 0,5–1 mm na aresta de baixo
  reduz muito — e isso é geometria, não configuração de slicer.
- Priorize a face mais plana para baixo.
- Peça com razão altura/base acima de 4 é risco real na A1.

---

## Orientação e resistência

A peça quebra **entre camadas** muito antes de quebrar no plano XY — a
resistência na direção Z é tipicamente metade da resistência em XY.

Se ela vai sofrer esforço numa direção conhecida (gancho que puxa, alça que
segura peso), oriente para o esforço correr **ao longo** das camadas. Um gancho
impresso em pé quebra no primeiro uso; deitado, aguenta.

Isso frequentemente conflita com a regra de balanço. Quando conflitar,
resistência ganha em peça funcional; acabamento ganha em peça decorativa.

---

## Multicolor (AMS Lite)

- Partes de cores diferentes precisam ser **objetos separados**. Geometria
  fundida não vira duas cores.
- Troca de cor gasta purga e tempo: 4 cores numa peça pequena pode dobrar a
  duração. Avise quando passar de 2 cores.
- Troca **por altura** é bem mais barata que troca **por região** na mesma
  camada.

---

## Peça maior que a mesa

Não escale peça funcional para caber — escalar mata o requisito em silêncio.
Parta em módulos. Encaixes que funcionam bem em FDM:

- **Pino e furo**: pino Ø6 mm, furo com folga 0,2 mm (parâmetro `folga`), profundidade
  1,5× o diâmetro. Simples e forte com cola.
- **Rabo de andorinha**: mais forte sem cola, mas precisa de 0,3 mm de folga e
  imprime melhor com o eixo do encaixe na vertical.
- **Parafuso**: inserto de porca M3 embutido no desenho, com parafuso de metal.

Sempre marque orientação (um pino assimétrico, ou um chanfro num canto só) —
senão a montagem tem 4 jeitos de dar errado.

---

## Ordem de grandeza

O número real vem do slice; isto é só para decidir antes.

| Peça | Massa | Tempo |
|---|---|---|
| Chaveiro 5×3 cm | 7–10 g | 0,5–1 h |
| Suporte ou placa 12 cm | 25–40 g | 1,5–3 h |
| Organizador ou vaso 20 cm | 100–150 g | 6–10 h |

A validação do passo 1c dá o volume: × 1,24 g/cm³ (PLA) é um chute de massa
— conta só a parte sólida, o infill real pesa menos. Serve para decidir, não
para precificar — a precificação usa o número do slice.
