"""Caixa com tampa de encaixe: dois corpos lado a lado na mesa, duas cores.

slot1 = caixa (extrusão + shell aberto em cima), slot2 = tampa (placa + aba que
entra na caixa com `folga`). A tampa sai deitada, com a aba para cima: vire-a
depois de impressa. Mude só o bloco de parâmetros e rode o arquivo inteiro com
fusion_mcp_execute (featureType "script"). Cantos retos de propósito: com fillet
na caixa, a aba precisaria do mesmo raio interno menos a folga.
"""
import adsk.core
import adsk.fusion
import json

# --- parâmetros (mm) --------------------------------------------------------
COMPRIMENTO = 80.0     # externo
LARGURA = 60.0         # externo
ALTURA_CAMADAS = 334   # 334 x 0,12 = 40,08 mm
PAREDE_CAMADAS = 14    # 14 x 0,12 = 1,68 mm, vale para parede e fundo
TAMPA_CAMADAS = 17     # 17 x 0,12 = 2,04 mm
ABA_CAMADAS = 50       # 50 x 0,12 = 6,00 mm
ABA_PAREDE = 1.6       # espessura da aba
FOLGA = 0.2            # encaixe justo; 0,3 para solto (fdm-a1.md)
VAO = 10.0             # distância entre caixa e tampa na mesa
COR_CAIXA = '#34495e'
COR_TAMPA = '#e67e22'
# ----------------------------------------------------------------------------

CAMADA = 0.12
NB = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation


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
    up.add('altura', VI.createByString(f'{ALTURA_CAMADAS} * camada'), 'mm', 'caixa')
    up.add('parede', VI.createByString(f'{PAREDE_CAMADAS} * camada'), 'mm', 'parede e fundo')
    up.add('tampa', VI.createByString(f'{TAMPA_CAMADAS} * camada'), 'mm', 'placa da tampa')
    up.add('aba', VI.createByString(f'{ABA_CAMADAS} * camada'), 'mm', 'aba de encaixe')
    up.add('folga', VI.createByString(f'{FOLGA} mm'), 'mm', 'encaixe')

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

    parede = PAREDE_CAMADAS * CAMADA
    if ABA_CAMADAS * CAMADA >= ALTURA_CAMADAS * CAMADA - parede:
        raise RuntimeError('a aba é mais alta que o vão interno da caixa')

    # caixa: bloco cheio, depois shell tirando a face de cima
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.sketchCurves.sketchLines.addCenterPointRectangle(
        P(0, 0, 0), P(cm(COMPRIMENTO / 2), cm(LARGURA / 2), 0))
    caixa = ext.addSimple(sk.profiles.item(0), VI.createByString('altura'), NB).bodies.item(0)
    caixa.name = 'slot1_caixa'
    topo = max(caixa.faces, key=lambda f: f.centroid.z)
    faces = adsk.core.ObjectCollection.create()
    faces.add(topo)
    si = root.features.shellFeatures.createInput(faces, False)
    si.insideThickness = VI.createByString('parede')
    root.features.shellFeatures.add(si)
    colorir(caixa, COR_CAIXA)

    # tampa, ao lado da caixa em x
    cx = COMPRIMENTO + VAO
    sk2 = root.sketches.add(root.xYConstructionPlane)
    sk2.sketchCurves.sketchLines.addCenterPointRectangle(
        P(cm(cx), 0, 0), P(cm(cx + COMPRIMENTO / 2), cm(LARGURA / 2), 0))
    tampa = ext.addSimple(sk2.profiles.item(0), VI.createByString('tampa'), NB).bodies.item(0)
    tampa.name = 'slot2_tampa'

    # aba: anel retangular por dentro da parede da caixa, menos a folga
    meia_c = COMPRIMENTO / 2 - parede - FOLGA
    meia_l = LARGURA / 2 - parede - FOLGA
    pi = root.constructionPlanes.createInput()
    pi.setByOffset(root.xYConstructionPlane, VI.createByString('tampa'))
    plano = root.constructionPlanes.add(pi)
    sk3 = root.sketches.add(plano)
    R = sk3.sketchCurves.sketchLines.addCenterPointRectangle
    R(P(cm(cx), 0, 0), P(cm(cx + meia_c), cm(meia_l), 0))
    R(P(cm(cx), 0, 0), P(cm(cx + meia_c - ABA_PAREDE), cm(meia_l - ABA_PAREDE), 0))
    anel = min((sk3.profiles.item(i) for i in range(sk3.profiles.count)),
               key=lambda p: p.areaProperties().area)
    ai = ext.createInput(anel, JOIN)
    ai.setDistanceExtent(False, VI.createByString('aba'))
    ai.participantBodies = [tampa]
    ext.add(ai)
    colorir(tampa, COR_TAMPA)

    app.activeViewport.fit()
    print(json.dumps(dict(peca='caixa_tampa',
                          caixa_mm=[COMPRIMENTO, LARGURA, round(ALTURA_CAMADAS * CAMADA, 2)],
                          aba_mm=[round(2 * meia_c, 2), round(2 * meia_l, 2)],
                          total_mm=[2 * COMPRIMENTO + VAO, LARGURA,
                                    round(ALTURA_CAMADAS * CAMADA, 2)],
                          slots={1: COR_CAIXA, 2: COR_TAMPA}), ensure_ascii=False))
