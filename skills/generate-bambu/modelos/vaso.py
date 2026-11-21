"""Vaso: revolução do perfil da parede, uma cor.

slot1 = vaso. Mude só o bloco de parâmetros e rode o arquivo inteiro com
fusion_mcp_execute (featureType "script"). O perfil fica no plano XZ, onde o Y
do sketch é o −Z do mundo: por isso as alturas entram negativas no sketch.
Parede inclinada mais de 45° da vertical pede suporte, e o script recusa.
"""
import adsk.core
import adsk.fusion
import json
import math

# --- parâmetros (mm) --------------------------------------------------------
ALTURA_CAMADAS = 667   # 667 x 0,12 = 80,04 mm
RAIO_BASE = 30.0       # raio externo no pé
RAIO_TOPO = 40.0       # raio externo na boca
PAREDE = 1.6           # espessura horizontal (4 linhas de 0,4)
PISO_CAMADAS = 10      # 10 x 0,12 = 1,20 mm
COR = '#c0392b'
# ----------------------------------------------------------------------------

CAMADA = 0.12


def cm(mm):
    return mm / 10.0


def run(context):
    altura = ALTURA_CAMADAS * CAMADA
    piso = PISO_CAMADAS * CAMADA
    inclinacao = math.degrees(math.atan2(abs(RAIO_TOPO - RAIO_BASE), altura))
    if inclinacao > 45:
        raise RuntimeError(f'parede a {inclinacao:.0f}° da vertical pede suporte; '
                           'aproxime RAIO_BASE de RAIO_TOPO ou aumente a altura')
    if PAREDE < 0.8:
        raise RuntimeError('PAREDE abaixo de 0,8 mm não imprime com bico de 0,4')

    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    des.fusionUnitsManager.distanceDisplayUnits = \
        adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    root = des.rootComponent
    VI = adsk.core.ValueInput
    P = adsk.core.Point3D.create

    up = des.userParameters
    up.add('camada', VI.createByString(f'{CAMADA} mm'), 'mm', 'altura de camada')
    up.add('altura', VI.createByString(f'{ALTURA_CAMADAS} * camada'), 'mm', 'vaso')
    up.add('piso', VI.createByString(f'{PISO_CAMADAS} * camada'), 'mm', 'fundo')

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

    # raio externo na altura do piso, para a parede interna seguir a inclinação
    r_piso = RAIO_BASE + (RAIO_TOPO - RAIO_BASE) * piso / altura
    # (raio, altura) em mm; no sketch vira (x, -z)
    perfil = [(0, 0), (RAIO_BASE, 0), (RAIO_TOPO, altura), (RAIO_TOPO - PAREDE, altura),
              (r_piso - PAREDE, piso), (0, piso)]

    sk = root.sketches.add(root.xZConstructionPlane)
    L = sk.sketchCurves.sketchLines
    pts = [P(cm(r), cm(-z), 0) for r, z in perfil]
    for a, b in zip(pts, pts[1:] + pts[:1], strict=True):
        L.addByTwoPoints(a, b)
    eixo = L.addByTwoPoints(P(0, 0, 0), P(0, cm(-altura), 0))
    eixo.isConstruction = True

    rv = root.features.revolveFeatures
    ri = rv.createInput(sk.profiles.item(0), eixo,
                        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ri.setAngleExtent(False, VI.createByString('360 deg'))
    vaso = rv.add(ri).bodies.item(0)
    vaso.name = 'slot1_vaso'
    colorir(vaso, COR)

    bb = vaso.boundingBox
    z0, z1 = bb.minPoint.z * 10, bb.maxPoint.z * 10
    if abs(z0) > 1e-3 or abs(z1 - altura) > 1e-3:
        raise RuntimeError(f'vaso de z {z0:.2f} a {z1:.2f} mm: o perfil saiu invertido')

    app.activeViewport.fit()
    print(json.dumps(dict(peca='vaso', inclinacao_graus=round(inclinacao, 1),
                          total_mm=[2 * RAIO_TOPO, 2 * RAIO_TOPO, round(altura, 2)],
                          slots={1: COR}), ensure_ascii=False))
