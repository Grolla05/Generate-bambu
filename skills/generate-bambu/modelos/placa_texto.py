"""Placa com texto: letreiro retangular com moldura e texto em relevo.

slot1 = placa, slot2 = moldura, texto em slot2 se tiver a cor da moldura,
senão em slot3 (um slot = uma cor). Mude só o bloco de parâmetros e rode o
arquivo inteiro com fusion_mcp_execute (featureType "script"). O texto encolhe
até caber dentro da moldura — a caixa do setAsMultiLine não limita a largura.
"""
import adsk.core
import adsk.fusion
import json

# --- parâmetros (mm) --------------------------------------------------------
TEXTO = 'Bem-vindo'
LARGURA = 150.0
ALTURA = 50.0
RAIO_CANTO = 5.0
MOLDURA = 3.0          # largura da moldura em relevo
RECUO = 2.0            # distância da moldura até a beira da placa
MARGEM = 4.0           # folga entre moldura e texto
BASE_CAMADAS = 25      # 25 x 0,12 = 3,00 mm
RELEVO_CAMADAS = 7     # 7 x 0,12 = 0,84 mm
FONTE = 'Arial Black'
TEXTO_MIN_MM = 6.0
COR_BASE = '#ffffff'
COR_MOLDURA = '#222222'
COR_TEXTO = '#222222'
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
    up.add('relevo', VI.createByString(f'{RELEVO_CAMADAS} * camada'), 'mm', 'moldura e texto')

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

    def retangulo_arredondado(sk, meia_l, meia_a, raio):
        linhas = sk.sketchCurves.sketchLines.addCenterPointRectangle(
            P(0, 0, 0), P(cm(meia_l), cm(meia_a), 0))
        if raio > 0:
            for i in range(4):
                a, b = linhas.item(i), linhas.item((i + 1) % 4)
                sk.sketchCurves.sketchArcs.addFillet(
                    a, a.endSketchPoint.geometry, b, b.startSketchPoint.geometry, cm(raio))

    sk = root.sketches.add(root.xYConstructionPlane)
    retangulo_arredondado(sk, LARGURA / 2, ALTURA / 2, RAIO_CANTO)
    placa = ext.addSimple(sk.profiles.item(0), VI.createByString('base'), NB).bodies.item(0)
    placa.name = 'slot1_base'
    colorir(placa, COR_BASE)

    pi = root.constructionPlanes.createInput()
    pi.setByOffset(root.xYConstructionPlane, VI.createByString('base'))
    plano = root.constructionPlanes.add(pi)

    # moldura: dois retângulos arredondados, o perfil de menor área é o anel
    fora_l, fora_a = LARGURA / 2 - RECUO, ALTURA / 2 - RECUO
    r_fora = max(RAIO_CANTO - RECUO, 0)
    sk2 = root.sketches.add(plano)
    retangulo_arredondado(sk2, fora_l, fora_a, r_fora)
    retangulo_arredondado(sk2, fora_l - MOLDURA, fora_a - MOLDURA, max(r_fora - MOLDURA, 0))
    anel = min((sk2.profiles.item(i) for i in range(sk2.profiles.count)),
               key=lambda p: p.areaProperties().area)
    moldura = ext.addSimple(anel, VI.createByString('relevo'), NB).bodies.item(0)
    moldura.name = 'slot2_moldura'
    colorir(moldura, COR_MOLDURA)

    slot_texto = 2 if COR_TEXTO.lower() == COR_MOLDURA.lower() else 3
    livre_l = fora_l - MOLDURA - MARGEM
    livre_a = fora_a - MOLDURA - MARGEM
    sk3 = root.sketches.add(plano)
    txt, alt = texto_que_cabe(sk3, TEXTO, -livre_l, livre_l, 2 * livre_a)
    if alt < TEXTO_MIN_MM:
        raise RuntimeError(f'texto a {alt:.1f} mm fica abaixo de {TEXTO_MIN_MM} mm: '
                           'encurte o texto ou aumente LARGURA')
    letras = ext.addSimple(txt, VI.createByString('relevo'), NB)
    for i in range(letras.bodies.count):
        b = letras.bodies.item(i)
        b.name = f'slot{slot_texto}_texto_{i + 1}'
        colorir(b, COR_TEXTO)

    slots = {1: COR_BASE, 2: COR_MOLDURA}
    slots[slot_texto] = COR_TEXTO
    app.activeViewport.fit()
    print(json.dumps(dict(peca='placa_texto', texto_mm=round(alt, 2),
                          total_mm=[LARGURA, ALTURA,
                                    round((BASE_CAMADAS + RELEVO_CAMADAS) * CAMADA, 2)],
                          slots=slots), ensure_ascii=False))
