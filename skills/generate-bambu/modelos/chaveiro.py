"""Chaveiro: placa com furo de argola e nome em relevo, duas cores.

slot1 = placa, slot2 = nome (uma letra por corpo, todas slot2_).
Mude só o bloco de parâmetros e rode o arquivo inteiro com fusion_mcp_execute
(featureType "script"). O nome encolhe até caber ao lado do furo; abaixo de
TEXTO_MIN_MM o script para com erro em vez de gerar letra que não imprime.
"""
import adsk.core
import adsk.fusion
import json

# --- parâmetros (mm) --------------------------------------------------------
NOME = 'Felipe'
LARGURA = 60.0
ALTURA = 30.0
RAIO_CANTO = 4.0
FURO = 5.0             # diâmetro da argola
MARGEM = 3.0           # borda livre em volta do furo e do nome
BASE_CAMADAS = 25      # 25 x 0,12 = 3,00 mm
RELEVO_CAMADAS = 7     # 7 x 0,12 = 0,84 mm
FONTE = 'Arial Black'
TEXTO_MIN_MM = 6.0
COR_BASE = '#1f4e9c'
COR_TEXTO = '#ffffff'
# ----------------------------------------------------------------------------

CAMADA = 0.12
NB = adsk.fusion.FeatureOperations.NewBodyFeatureOperation


def cm(mm):
    return mm / 10.0


def run(context):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    des.fusionUnitsManager.distanceDisplayUnits = \
        adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    root = des.rootComponent
    VI = adsk.core.ValueInput
    P = adsk.core.Point3D.create
    ext = root.features.extrudeFeatures

    up = des.userParameters
    up.add('camada', VI.createByString(f'{CAMADA} mm'), 'mm', 'altura de camada')
    up.add('base', VI.createByString(f'{BASE_CAMADAS} * camada'), 'mm', 'placa')
    up.add('relevo', VI.createByString(f'{RELEVO_CAMADAS} * camada'), 'mm', 'nome')

    lib = app.materialLibraries.itemByName('Fusion Appearance Library')
    modelo = lib.appearances.itemByName('Paint - Enamel Glossy (Yellow)')

    def colorir(body, hexcor):
        nome = 'cor_' + hexcor.lower()
        a = des.appearances.itemByName(nome)
        if not a:
            a = des.appearances.addByCopy(modelo, nome)
            r, g, b = (int(hexcor[i:i + 2], 16) for i in (1, 3, 5))
            for p in a.appearanceProperties:
                if isinstance(p, adsk.core.ColorProperty) and \
                   p.id in ('opaque_albedo', 'generic_diffuse'):
                    p.value = adsk.core.Color.create(r, g, b, 255)
        body.appearance = a

    def texto_que_cabe(sk, texto, x0, x1, alt_max):
        """Texto centrado entre x0 e x1 (mm); encolhe até caber. Devolve (texto, altura)."""
        alt = alt_max
        for _ in range(8):
            ti = sk.sketchTexts.createInput2(texto, cm(alt))
            ti.setAsMultiLine(P(cm(x0), cm(-alt_max / 2), 0), P(cm(x1), cm(alt_max / 2), 0),
                              adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                              adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
            ti.fontName = FONTE
            st = sk.sketchTexts.add(ti)
            bb = st.boundingBox
            larg = (bb.maxPoint.x - bb.minPoint.x) * 10
            if larg <= (x1 - x0) + 1e-3:
                return st, alt
            st.deleteMe()
            alt *= (x1 - x0) / larg * 0.97
        raise RuntimeError('texto não coube depois de 8 tentativas')

    # placa com furo
    x_furo = -LARGURA / 2 + MARGEM + FURO / 2
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.sketchCurves.sketchLines.addCenterPointRectangle(
        P(0, 0, 0), P(cm(LARGURA / 2), cm(ALTURA / 2), 0))
    sk.sketchCurves.sketchCircles.addByCenterRadius(P(cm(x_furo), 0, 0), cm(FURO / 2))
    prof = max((sk.profiles.item(i) for i in range(sk.profiles.count)),
               key=lambda p: p.areaProperties().area)
    base = ext.addSimple(prof, VI.createByString('base'), NB).bodies.item(0)
    base.name = 'slot1_base'

    # cantos arredondados: só arestas retas verticais (círculo tem início == fim)
    arestas = adsk.core.ObjectCollection.create()
    for ed in base.edges:
        s, t = ed.startVertex.geometry, ed.endVertex.geometry
        if abs(s.x - t.x) < 1e-6 and abs(s.y - t.y) < 1e-6 and abs(s.z - t.z) > 1e-6:
            arestas.add(ed)
    fi = root.features.filletFeatures.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(arestas, VI.createByString(f'{RAIO_CANTO} mm'), True)
    root.features.filletFeatures.add(fi)
    colorir(base, COR_BASE)

    # nome em relevo, num plano no topo da placa
    pi = root.constructionPlanes.createInput()
    pi.setByOffset(root.xYConstructionPlane, VI.createByString('base'))
    plano = root.constructionPlanes.add(pi)
    sk2 = root.sketches.add(plano)
    x0 = x_furo + FURO / 2 + MARGEM
    x1 = LARGURA / 2 - MARGEM
    txt, alt = texto_que_cabe(sk2, NOME, x0, x1, ALTURA - 2 * MARGEM)
    if alt < TEXTO_MIN_MM:
        raise RuntimeError(f'nome a {alt:.1f} mm fica abaixo de {TEXTO_MIN_MM} mm: '
                           'encurte o nome ou aumente LARGURA')
    letras = ext.addSimple(txt, VI.createByString('relevo'), NB)
    for i in range(letras.bodies.count):
        b = letras.bodies.item(i)
        b.name = f'slot2_texto_{i + 1}'
        colorir(b, COR_TEXTO)

    app.activeViewport.fit()
    print(json.dumps(dict(peca='chaveiro', texto_mm=round(alt, 2),
                          total_mm=[LARGURA, ALTURA,
                                    round((BASE_CAMADAS + RELEVO_CAMADAS) * CAMADA, 2)],
                          slots={1: COR_BASE, 2: COR_TEXTO}), ensure_ascii=False))
