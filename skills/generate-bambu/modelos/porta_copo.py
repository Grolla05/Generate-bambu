"""Porta-copo redondo: disco com borda e texto em relevo, duas cores.

slot1 = disco, slot2 = borda + texto (mesma cor, mesmo slot).
Mude só o bloco de parâmetros e rode o arquivo inteiro com fusion_mcp_execute
(featureType "script"). Chanfro na aresta de baixo contra empenamento. O texto
encolhe até caber no miolo; TEXTO = '' deixa só a borda.
"""
import adsk.core
import adsk.fusion
import json

# --- parâmetros (mm) --------------------------------------------------------
DIAMETRO = 90.0
TEXTO = 'Casa'
BORDA = 3.0            # largura do anel em relevo
RECUO = 1.0            # distância do anel até a beira do disco
MARGEM = 4.0           # folga entre anel e texto
BASE_CAMADAS = 30      # 30 x 0,12 = 3,60 mm
RELEVO_CAMADAS = 6     # 6 x 0,12 = 0,72 mm
CHANFRO = 0.6
FONTE = 'Arial Black'
TEXTO_MIN_MM = 6.0
COR_BASE = '#2d6a4f'
COR_RELEVO = '#f1c40f'
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
    up.add('base', VI.createByString(f'{BASE_CAMADAS} * camada'), 'mm', 'disco')
    up.add('relevo', VI.createByString(f'{RELEVO_CAMADAS} * camada'), 'mm', 'borda e texto')

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

    raio = DIAMETRO / 2
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.sketchCurves.sketchCircles.addByCenterRadius(P(0, 0, 0), cm(raio))
    disco = ext.addSimple(sk.profiles.item(0), VI.createByString('base'), NB).bodies.item(0)
    disco.name = 'slot1_base'

    # chanfro só na aresta circular de baixo (z = 0), antes do relevo
    arestas = adsk.core.ObjectCollection.create()
    for ed in disco.edges:
        if abs(ed.boundingBox.maxPoint.z) < 1e-6:
            arestas.add(ed)
    ci = root.features.chamferFeatures.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(
        arestas, VI.createByString(f'{CHANFRO} mm'), True)
    root.features.chamferFeatures.add(ci)
    colorir(disco, COR_BASE)

    pi = root.constructionPlanes.createInput()
    pi.setByOffset(root.xYConstructionPlane, VI.createByString('base'))
    plano = root.constructionPlanes.add(pi)

    # anel: dois círculos, o perfil de menor área é o anel
    r_fora = raio - RECUO
    r_dentro = r_fora - BORDA
    sk2 = root.sketches.add(plano)
    sk2.sketchCurves.sketchCircles.addByCenterRadius(P(0, 0, 0), cm(r_fora))
    sk2.sketchCurves.sketchCircles.addByCenterRadius(P(0, 0, 0), cm(r_dentro))
    anel_prof = min((sk2.profiles.item(i) for i in range(sk2.profiles.count)),
                    key=lambda p: p.areaProperties().area)
    anel = ext.addSimple(anel_prof, VI.createByString('relevo'), NB).bodies.item(0)
    anel.name = 'slot2_borda'
    colorir(anel, COR_RELEVO)

    alt = None
    if TEXTO:
        # retângulo inscrito no miolo: largura 2·r·cos30, altura r (folgado)
        r_livre = r_dentro - MARGEM
        meia = r_livre * 0.866
        sk3 = root.sketches.add(plano)
        txt, alt = texto_que_cabe(sk3, TEXTO, -meia, meia, r_livre)
        if alt < TEXTO_MIN_MM:
            raise RuntimeError(f'texto a {alt:.1f} mm fica abaixo de {TEXTO_MIN_MM} mm: '
                               'encurte o texto ou aumente DIAMETRO')
        letras = ext.addSimple(txt, VI.createByString('relevo'), NB)
        for i in range(letras.bodies.count):
            b = letras.bodies.item(i)
            b.name = f'slot2_texto_{i + 1}'
            colorir(b, COR_RELEVO)

    app.activeViewport.fit()
    print(json.dumps(dict(peca='porta_copo', texto_mm=alt and round(alt, 2),
                          total_mm=[DIAMETRO, DIAMETRO,
                                    round((BASE_CAMADAS + RELEVO_CAMADAS) * CAMADA, 2)],
                          slots={1: COR_BASE, 2: COR_RELEVO}), ensure_ascii=False))
