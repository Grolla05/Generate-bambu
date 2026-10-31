"""Transforma slots de malha num projeto nativo do Bambu Studio.

Um 3MF padrão só vira peça multicor pelos diálogos da interface. Este projeto já nasce
como o Bambu Studio salva: um objeto pai com uma parte por slot, com `extruder` em
`model_settings.config` e a configuração em `project_settings.config`. Assim o CLI fatia
sem soltar o relevo da base e a interface abre sem diálogo nenhum.

Stdlib pura.
"""

import json
import uuid
import zipfile
from xml.sax.saxutils import quoteattr

MESA_MM = 256.0
MARGEM_MM = 3.0
# A torre de purga mora no canto de cima à esquerda: x até 60 e do y dela até o fim da mesa.
TORRE_X_MM = 60.0
FOLGA_TORRE_MM = 5.0

_NS = (
    'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
    'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
    'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
    'requiredextensions="p"'
)
_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="model" '
    'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
    '<Default Extension="png" ContentType="image/png"/></Types>'
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="{}" Id="rel-1" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
)
_OBJETOS = "/3D/Objects/object_1.model"


class ErroPeca(ValueError):
    """A peça não cabe na mesa do jeito que o fatiamento precisa."""


def caixa(slots):
    """(xmin, ymin, zmin, xmax, ymax, zmax) de todos os slots juntos."""
    pontos = [v for s in slots for v in s["verts"]]
    if not pontos:
        raise ErroPeca("nenhuma malha para fatiar")
    x, y, z = zip(*pontos, strict=True)
    return min(x), min(y), min(z), max(x), max(y), max(z)


def posicionar(largura, profundidade, n_slots, y_torre):
    """(x0, y0) do canto da peça na mesa, ou None se não sobrar lugar para a torre.

    Centra sempre que der. Multicor que invade a torre anda o mínimo para sair dela.
    """
    x0, y0 = (MESA_MM - largura) / 2, (MESA_MM - profundidade) / 2
    limite_y = y_torre - FOLGA_TORRE_MM
    if n_slots == 1 or x0 >= TORRE_X_MM or y0 + profundidade <= limite_y:
        return x0, y0
    opcoes = []
    if TORRE_X_MM + largura <= MESA_MM - MARGEM_MM:
        opcoes.append((TORRE_X_MM - x0, TORRE_X_MM, y0))
    if limite_y - profundidade >= MARGEM_MM:
        opcoes.append((y0 + profundidade - limite_y, x0, limite_y - profundidade))
    if not opcoes:
        return None
    _, x, y = min(opcoes)
    return x, y


def _modelo_objetos(slots, dx, dy, dz):
    linhas = [
        f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {_NS}>',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        " <resources>",
    ]
    for i, s in enumerate(slots, 1):
        linhas.append(f'  <object id="{i}" p:UUID="{uuid.uuid4()}" type="model"><mesh><vertices>')
        linhas += [f'<vertex x="{x + dx:.6f}" y="{y + dy:.6f}" z="{z + dz:.6f}"/>'
                   for x, y, z in s["verts"]]
        linhas.append("</vertices><triangles>")
        linhas += [f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in s["tris"]]
        linhas.append("</triangles></mesh></object>")
    linhas += [" </resources>", " <build/>", "</model>"]
    return "\n".join(linhas)


def _modelo_raiz(n, pai, x, y, versao):
    componentes = "".join(
        f'<component p:path="{_OBJETOS}" objectid="{i}" p:UUID="{uuid.uuid4()}" '
        'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
        for i in range(1, n + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<model unit="millimeter" xml:lang="en-US" {_NS}>\n'
        f' <metadata name="Application">BambuStudio-{versao}</metadata>\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        f' <resources><object id="{pai}" p:UUID="{uuid.uuid4()}" type="model">'
        f"<components>{componentes}</components></object></resources>\n"
        f' <build p:UUID="{uuid.uuid4()}"><item objectid="{pai}" p:UUID="{uuid.uuid4()}" '
        f'transform="1 0 0 0 1 0 0 0 1 {x:.6f} {y:.6f} 0" printable="1"/></build>\n</model>'
    )


def _model_settings(slots, pai, nome):
    partes = []
    for i, s in enumerate(slots, 1):
        partes.append(
            f'    <part id="{i}" subtype="normal_part" uuid="{uuid.uuid4()}">\n'
            f'      <metadata key="name" value={quoteattr(s["slot"])}/>\n'
            '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
            f'      <metadata key="extruder" value="{i}"/>\n'
            f'      <mesh_stat face_count="{len(s["tris"])}" edges_fixed="0" '
            'degenerate_facets="0" facets_removed="0" facets_reversed="0" '
            'backwards_edges="0"/>\n    </part>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
        f'  <object id="{pai}">\n    <metadata key="name" value={quoteattr(nome)}/>\n'
        '    <metadata key="extruder" value="1"/>\n' + "\n".join(partes) + "\n  </object>\n"
        '  <plate>\n    <metadata key="plater_id" value="1"/>\n'
        '    <metadata key="plater_name" value=""/>\n'
        '    <metadata key="locked" value="false"/>\n'
        f'    <model_instance>\n      <metadata key="object_id" value="{pai}"/>\n'
        '      <metadata key="instance_id" value="0"/>\n'
        '      <metadata key="identify_id" value="1"/>\n'
        "    </model_instance>\n  </plate>\n</config>"
    )


def gravar_projeto(slots, saida, configuracao, nome, versao, posicao):
    """Grava o projeto com a peça em `posicao` (canto x0, y0) e a base em z = 0."""
    xmin, ymin, zmin, xmax, ymax, _ = caixa(slots)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    n, pai = len(slots), len(slots) + 1
    x = posicao[0] + (xmax - xmin) / 2
    y = posicao[1] + (ymax - ymin) / 2
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS.format("/3D/3dmodel.model"))
        z.writestr("3D/3dmodel.model", _modelo_raiz(n, pai, x, y, versao))
        z.writestr("3D/_rels/3dmodel.model.rels", _RELS.format(_OBJETOS))
        z.writestr(_OBJETOS.lstrip("/"), _modelo_objetos(slots, -cx, -cy, -zmin))
        z.writestr("Metadata/model_settings.config", _model_settings(slots, pai, nome))
        z.writestr("Metadata/project_settings.config", json.dumps(configuracao, indent=1))
