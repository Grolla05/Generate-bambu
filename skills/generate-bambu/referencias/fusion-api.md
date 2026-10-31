# Fusion via MCP — receitas testadas

Consulta. Pule para a seção que a peça pede. Tudo aqui foi rodado no Fusion
do usuário (versão 2705, Python 3.14) pelo `fusion_mcp_execute`.

---

## Contrato do script

- `featureType: "script"`, código em `object.script`.
- **Precisa definir `run(context)`.** Código só no nível do módulo dá
  `NameError: name 'run' is not defined`.
- `print()` volta em `message`. Erro volta com traceback em `error`.
- Script que só lê o design: `readOnly: true` (roda mesmo com diálogo aberto,
  e o MCP recusa qualquer escrita).
- **A unidade interna da API é centímetro.** Ponto `Point3D.create(3, 1.5, 0)`
  é 30 × 15 mm. Volume volta em cm³ (× 1000 → mm³). Para não errar, passe
  distância como texto: `ValueInput.createByString('2.04 mm')` ou o nome de um
  parâmetro (`'base'`).
- Cada script é uma transação: `fusion_mcp_update → undo` desfaz o script
  inteiro.

```python
import adsk.core, adsk.fusion, json

def run(context):
    app = adsk.core.Application.get()
    des = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent
    VI = adsk.core.ValueInput
    P = adsk.core.Point3D.create
    ...
```

---

## Documento novo, paramétrico, em mm

```python
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
des = adsk.fusion.Design.cast(app.activeProduct)
des.designType = adsk.fusion.DesignTypes.ParametricDesignType
des.fusionUnitsManager.distanceDisplayUnits = \
    adsk.fusion.DistanceUnits.MillimeterDistanceUnits
root = des.rootComponent          # OBRIGATÓRIO: o root anterior é do design antigo

up = des.userParameters
up.add('camada', VI.createByString('0.12 mm'), 'mm', 'altura de camada')
up.add('base',   VI.createByString('17 * camada'), 'mm', '2,04 mm')
up.add('relevo', VI.createByString('7 * camada'),  'mm', '0,84 mm')
up.add('folga',  VI.createByString('0.2 mm'), 'mm', 'encaixe justo')
```

**Toda altura é `N * camada`.** É assim que a regra de 0,12 mm vira geometria:
quem pedir 0,8 mm recebe `7 * camada` = 0,84 mm, e isso vai na mensagem.
Ajuste depois é `up.itemByName('relevo').expression = '9 * camada'`.

---

## Sketch e extrusão

```python
sk = root.sketches.add(root.xYConstructionPlane)
sk.sketchCurves.sketchLines.addCenterPointRectangle(P(0,0,0), P(3,1.5,0))  # 60×30
sk.sketchCurves.sketchCircles.addByCenterRadius(P(-2.3,0,0), 0.35)          # furo Ø7
# o perfil com furo é o de maior área
prof = max((sk.profiles.item(i) for i in range(sk.profiles.count)),
           key=lambda p: p.areaProperties().area)
ext = root.features.extrudeFeatures
e1 = ext.addSimple(prof, VI.createByString('base'),
                   adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
b1 = e1.bodies.item(0); b1.name = 'slot1_base'
```

**Camada de cor por cima da base:** plano deslocado pelo parâmetro, sketch
nele, extrusão como **corpo novo** (cor diferente = corpo diferente; nunca
`Join` entre cores).

```python
pi = root.constructionPlanes.createInput()
pi.setByOffset(root.xYConstructionPlane, VI.createByString('base'))
plano = root.constructionPlanes.add(pi)
sk2 = root.sketches.add(plano)
sk2.sketchCurves.sketchCircles.addByCenterRadius(P(2.35,0,0), 0.4)  # Ø8, x 19,5..27,5 mm
e2 = ext.addSimple(sk2.profiles.item(0), VI.createByString('relevo'),
                   adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
e2.bodies.item(0).name = 'slot2_detalhe'
```

Gravado (rebaixo) na mesma cor: `CutFeatureOperation` com distância negativa.
Gravado com outra cor no fundo: corte na base **e** corpo novo da outra cor
preenchendo o rebaixo — dois corpos encostados, sem sobrepor.

---

## Texto

```python
sk = root.sketches.add(plano)
ti = sk.sketchTexts.createInput2('BUBBLE', 0.6)          # altura 6 mm
ti.setAsMultiLine(P(-1.5,-0.5,0), P(1.5,0.5,0),      # centrado em x = 0
                  adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                  adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
ti.fontName = 'Arial'
txt = sk.sketchTexts.add(ti)
e = ext.addSimple(txt, VI.createByString('relevo'),
                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
for i in range(e.bodies.count):
    e.bodies.item(i).name = f'slot3_texto_{i+1}'
```

**Pegadinha testada:** a caixa do `setAsMultiLine` **não limita a largura** —
o texto transborda dela. "BUBBLE" a 6 mm em Arial mede ~32 mm (≈ 5,4 mm por
letra). Depois de extrudar, leia a bounding box das letras e confirme que não
invadem furo nem outra cor; a validação 1c pega a sobreposição, mas é melhor
dimensionar antes.

**Outra pegadinha testada:** texto extrudado vira **um corpo por letra** (BUBBLE →
6 corpos, fora da ordem de leitura), e `Combine/Join` de corpos que não se tocam não une — o Fusion
devolve os corpos separados de novo. Não brigue com isso: nomeie todos com o
mesmo `slotN_` e o `agrupar_3mf.py` junta no passo 3.

Texto pequeno: altura ≥ 6 mm em relevo, ≥ 8 mm gravado; traço ≥ 0,8 mm.
Fonte com serifa fina some — prefira Arial, Arial Black, Verdana.

---

## Revolução (vaso, pote, cúpula, anel)

```python
sk = root.sketches.add(root.xZConstructionPlane)
L = sk.sketchCurves.sketchLines
# perfil da PAREDE, fechado; aqui raio 15→20 mm, altura 30 mm, parede 1,2, piso 1,2
pts = [(0,0),(1.5,0),(2.0,-3.0),(1.88,-3.0),(1.38,-0.12),(0,-0.12)]
for a, b in zip(pts, pts[1:] + pts[:1]):
    L.addByTwoPoints(P(a[0],a[1],0), P(b[0],b[1],0))
eixo = L.addByTwoPoints(P(0,0,0), P(0,-3,0)); eixo.isConstruction = True
rv = root.features.revolveFeatures
ri = rv.createInput(sk.profiles.item(0), eixo,
                    adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
ri.setAngleExtent(False, VI.createByString('360 deg'))
corpo = rv.add(ri).bodies.item(0); corpo.name = 'slot1_vaso'
```

**Pegadinha testada:** no plano XZ, o **Y do sketch é o −Z do mundo**. Por isso
as alturas do perfil acima são negativas: y = −3 cm vira z = +30 mm. Confira
com a bounding box (z de 0 a 30) depois de criar.

Parede inclinada mais de 45° da vertical pede suporte — feche o perfil dentro
disso. Ângulo parcial (`'90 deg'`) faz cotovelo e setor.

Alternativa mais curta para pote/copo: extrusão do contorno + `shellFeatures`
removendo a face de cima, espessura `'1.2 mm'`.

---

## Acabamento: fillet e chamfer

```python
# arestas verticais da placa (b1, do exemplo de extrusão) — em corpo de
# revolução não há aresta reta vertical: escolha as arestas de outro jeito
arestas = adsk.core.ObjectCollection.create()
for ed in b1.edges:
    s, t = ed.startVertex.geometry, ed.endVertex.geometry
    if abs(s.x-t.x) < 1e-6 and abs(s.y-t.y) < 1e-6:     # arestas verticais
        arestas.add(ed)
# fillet ANTES das camadas de cor: depois, o relevo pode ficar para fora da borda
fi = root.features.filletFeatures.createInput()
fi.edgeSetInputs.addConstantRadiusEdgeSet(arestas, VI.createByString('3 mm'), True)
root.features.filletFeatures.add(fi)
```

Chanfro de 0,5–1 mm na aresta de **baixo** reduz empenamento (`fdm-a1.md`):
`chamferFeatures.createInput2()` + `chamferEdgeSets.addEqualDistanceChamferEdgeSet`.
Rosca de verdade: `threadFeatures` (o parafuso ainda pede folga de 0,3 mm).

---

## Cor: uma appearance por corpo

```python
lib = app.materialLibraries.itemByName('Fusion Appearance Library')
modelo = lib.appearances.itemByName('Paint - Enamel Glossy (Yellow)')

def colorir(body, hexcor):
    nome = 'cor_' + hexcor.lower()                       # ex.: cor_#e8b647
    a = des.appearances.itemByName(nome)
    if not a:
        a = des.appearances.addByCopy(modelo, nome)
        r, g, b = (int(hexcor[i:i+2], 16) for i in (1, 3, 5))
        for p in a.appearanceProperties:
            if isinstance(p, adsk.core.ColorProperty) and \
               p.id in ('opaque_albedo', 'generic_diffuse'):
                p.value = adsk.core.Color.create(r, g, b, 255)
    body.appearance = a
```

Testado: o 3MF exportado sai com a cor exata (`#E8B647FF`). Corpo sem
appearance sai no cinza padrão `#A0A0A0` — o `agrupar_3mf` avisa. Todos os
corpos de um mesmo `slotN` levam a mesma cor.

---

## Validação (passo 1c) — script readOnly

Antes de rodar, ponha em `LIMITE_MM` e `SLOTS` os valores de `maquina` em
`python scripts/config.py mostrar`. `CURVA = True` só para topo de forma curva, como
vaso com borda arredondada: altura fora de camada vira aviso, e isso vai na mensagem.

```python
import adsk.core, adsk.fusion, json, re

LIMITE_MM = 250
SLOTS = 4
CURVA = False
RE_SLOT = r'^slot(0|[1-9]\d*)_.+$'
RE_COR = r'^(?:cor|bubble)_(#[0-9a-f]{6})$'

def run(context):
    app = adsk.core.Application.get()
    des = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent
    erros, avisos, out, cores = [], [], {}, {}
    parametro = des.userParameters.itemByName('camada')
    cam = parametro.value if parametro else None                # cm
    if cam is None:
        erros.append('parâmetro camada ausente')
    for comp in des.allComponents:
        if comp.id != root.id and comp.bRepBodies.count:
            erros.append(f'{comp.name}: corpo em subcomponente; mova para a raiz')
    corpos = list(root.bRepBodies)
    if not corpos:
        erros.append('design sem corpos')
    for b in corpos:
        bb = b.boundingBox
        z0, z1 = bb.minPoint.z, bb.maxPoint.z
        m = re.match(RE_SLOT, b.name)
        slot = int(m.group(1)) if m else 0
        cor = b.appearance.name if b.appearance else None
        c = re.match(RE_COR, cor or '')
        em_camadas = cam is not None and all(abs(v/cam - round(v/cam)) < 1e-3 for v in (z0, z1))
        if not 1 <= slot <= SLOTS:
            erros.append(f'{b.name}: nome fora do contrato slotN_descricao, N de 1 a {SLOTS}')
        if not b.isSolid:
            erros.append(f'{b.name}: corpo não sólido')
        if not c:
            erros.append(f'{b.name}: cor {cor} fora do padrão cor_#rrggbb')
        elif slot:
            cores.setdefault(slot, set()).add(c.group(1))
        if cam is not None and not em_camadas:
            (avisos if CURVA else erros).append(f'{b.name}: altura fora de múltiplo da camada')
        out[b.name] = dict(
            vol_mm3=round(b.volume * 1000, 2),
            x=round((bb.maxPoint.x-bb.minPoint.x)*10, 2),
            y=round((bb.maxPoint.y-bb.minPoint.y)*10, 2),
            z=[round(z0*10, 3), round(z1*10, 3)],
            z_em_camadas=em_camadas, cor=cor)
    for slot, usadas in cores.items():
        if len(usadas) > 1:
            erros.append(f'slot{slot}: corpos com cores diferentes {sorted(usadas)}')
    # união das caixas dos CORPOS (root.boundingBox inclui sketches e planos)
    tudo, interf = [0, 0, 0], []
    if corpos:
        bbs = [b.boundingBox for b in corpos]
        mn = [min(getattr(c.minPoint, k) for c in bbs) for k in 'xyz']
        mx = [max(getattr(c.maxPoint, k) for c in bbs) for k in 'xyz']
        tudo = [round((a - b) * 10, 2) for a, b in zip(mx, mn)]
    if any(v > LIMITE_MM for v in tudo):
        erros.append(f'peça de {tudo} mm não cabe em {LIMITE_MM} mm')
    if len(corpos) > 1:
        colecao = adsk.core.ObjectCollection.create()
        for b in corpos: colecao.add(b)
        interf = [(r.entityOne.name, r.entityTwo.name,
                   round(r.interferenceBody.volume*1000, 3))
                  for r in des.analyzeInterference(des.createInterferenceInput(colecao))]
    if interf:
        erros.append(f'volumes sobrepostos: {interf}')
    print(json.dumps(dict(ok=not erros, erros=erros, avisos=avisos, corpos=out,
                          total_mm=tudo, n_slots=len(cores), interferencias=interf),
                     ensure_ascii=False))
```

Precisa dar `ok: true`. A lista `erros` diz o que corrigir, e `avisos` vai na mensagem.
Corpo sem cor atribuída aparece como `Steel - Satin`, o padrão do Fusion, e cai em
`erros`. Faces encostadas (camada de cor sobre a base) **não** contam como
interferência; volume sobreposto conta, e é defeito: cor misturada na mesma região.

---

## Screenshot

`fusion_mcp_read` com `queryType: "screenshot"`, `direction` em
`iso-top-right`, `front`, `top` (e `bottom` se a face de baixo importar),
`width: 800, height: 500`. Antes, enquadre: `app.activeViewport.fit()` no fim
do script de modelagem.

---

## Salvar no projeto "Bubble Studio 3D"

```python
dp = app.data.dataProjects
proj = next((dp.item(i) for i in range(dp.count)
             if dp.item(i).name == 'Bubble Studio 3D'), None)
if proj is None:
    proj = dp.add('Bubble Studio 3D')
app.activeDocument.saveAs('Porta-copo Girassol', proj.rootFolder,
                          'generate-bambu', '')
```

Na primeira peça o projeto ainda não existe (o hub tinha só Admin Project,
Assets, Default Project) — o código cria. O salvamento sobe para a nuvem em
segundo plano. Nas voltas de ajuste: `app.activeDocument.save('ajuste: …')`
gera versão nova do mesmo documento.

Se `saveAs` falhar (sem rede, hub offline), siga sem salvar e diga isso numa
linha — o 3MF não depende do documento salvo.

---

## Exportar o 3MF (passo 3)

```python
import adsk.core, adsk.fusion, json, os, tempfile
def run(context):
    ...
    bruto = os.path.join(tempfile.gettempdir(), 'bubble_bruto.3mf')
    opt = des.exportManager.createC3MFExportOptions(root, bruto)
    opt.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    des.exportManager.execute(opt)
    final = '<pasta_saida>/porta-copo-girassol.3mf'   # do diagnostico.py
    os.makedirs(os.path.dirname(final), exist_ok=True)
    rel = agrupar_por_slot(bruto, final)        # colado de helpers/agrupar_3mf.py
    os.remove(bruto)
    print(json.dumps(rel, ensure_ascii=False))
```

Cole o conteúdo inteiro de `helpers/agrupar_3mf.py` no **começo** do script
(o Fusion não enxerga os arquivos da skill). Testado: o Fusion exporta um
`<object>` por corpo, nomeado, em `millimeter`, com a cor; o agrupamento
devolve um objeto por slot com malhas fechadas e volume igual ao do B-rep
(diferença < 0,1 %).

**Cor no Bambu Studio — testado:** o 3MF bruto do Fusion põe a cor só no
objeto, e o Bambu Studio **ignora** essa forma (cria filamentos com cores
padrão e deixa tudo no filamento 1). Por isso o `agrupar_3mf` grava a cor
também por triângulo (`colorgroup` + `pid/p1`): aí o Bambu Studio abre o
diálogo *Standard 3mf Import color* com as cores certas. Nunca mande o 3MF
bruto do Fusion para o slicer.

`MeshRefinementHigh` dá desvio de ~0,014 mm (um furo de Ø20 sai com ~190
lados) — abaixo do que a A1 resolve, então **não há compensação de polígono
inscrito a fazer**. Não use `isOneFilePerBody` nem `sendToPrintUtility`: o
arquivo é um só e quem abre o Bambu Studio é o passo 5.

---

## Fechar e desfazer

- Desfazer o último script: `fusion_mcp_update` `{featureType: "undo"}`.
- Documento de teste: `app.activeDocument.close(False)` (descarta).
- Documentos abertos: `fusion_mcp_read` `{queryType: "document", operation: "open"}`.

---

## Placa de calibração

Uma vez, antes de confiar nas medidas de encaixe. ~12 g, ~40 min.

Placa 90 × 50 mm, altura `34 * camada` (4,08 mm), cantos com fillet de 3 mm,
um corpo `slot1_calibracao`:

- Fileira de cima (y = +14 mm), furos de **4 · 6 · 8 · 10 · 12 mm** em
  x = −34, −20, −5, 12, 31 mm, modelados no nominal.
- Embaixo (y = −12 mm): furo de **20 mm** nominal em x = −25 e furo de
  **20 mm + 2 × 0,2** (folga justa) em x = 5 — o par mostra se a folga padrão
  basta para um pino de 20 mm.
- Quatro paredes de 8 mm de comprimento com **0,8 · 1,2 · 1,6 · 2,4 mm** de
  espessura, em x = 22, 27, 32, 37 mm, y = −12 — mostram o que o slicer
  imprime de verdade.

Meça os furos no paquímetro. O desvio sistemático (furo saindo, por exemplo,
0,15 mm menor em todos) é a **folga de processo** da máquina: grave no
parâmetro `folga` das peças seguintes e anote na nota de Tecnologia do vault.
