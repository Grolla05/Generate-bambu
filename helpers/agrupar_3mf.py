"""Agrupa os objetos de um .3mf exportado pelo Fusion: um objeto por slot do AMS.

Por que existe: o Fusion exporta um <object> por corpo. Texto extrudado vira
um corpo por letra, e corpos que não se tocam não podem ser unidos com Combine.
Sem agrupar, "BUBBLE" chega ao Bambu Studio como 6 objetos, e cada letra
pede um clique de filamento.

Regra de agrupamento: o nome do corpo começa com "slotN_" (slot1_base,
slot3_texto_B...). Todos os corpos com o mesmo "slotN" viram um objeto só,
com várias cascas (shells) — válido em 3MF e lido normalmente pelo slicer.
Corpo sem prefixo slotN é recusado: nome de corpo é contrato do fluxo.

Cor: grava basematerials por objeto e colorgroup por triângulo — o Bambu
Studio só reconhece a segunda forma em 3MF que não foi feito por ele.

Stdlib pura. Roda DENTRO do Fusion: cole este arquivo inteiro no começo do
script do passo 3 e chame agrupar_por_slot(). Também roda fora do Fusion.
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

NS_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_MAT = "http://schemas.microsoft.com/3dmanufacturing/material/2015/02"
_RE_SLOT = re.compile(r"^(slot\d+)", re.IGNORECASE)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="model" '
    'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
    '</Types>')
_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    '</Relationships>')


def _tabela_de_cores(raiz):
    """{id_do_recurso: [cor, cor, ...]} para colorgroup e basematerials."""
    t = {}
    for cg in raiz.iter(f"{{{NS_MAT}}}colorgroup"):
        t[cg.get("id")] = [c.get("color") for c in cg.iter(f"{{{NS_MAT}}}color")]
    for bm in raiz.iter(f"{{{NS_CORE}}}basematerials"):
        t[bm.get("id")] = [b.get("displaycolor") for b in bm.iter(f"{{{NS_CORE}}}base")]
    return t


def _matriz(txt):
    """Transform 3MF (12 números, linha a linha) -> função que aplica."""
    if not txt:
        return None
    m = [float(x) for x in txt.split()]
    def ap(x, y, z):
        return (x * m[0] + y * m[3] + z * m[6] + m[9],
                x * m[1] + y * m[4] + z * m[7] + m[10],
                x * m[2] + y * m[5] + z * m[8] + m[11])
    return ap


def _conferir_fechada(tris):
    """Toda aresta usada exatamente 2 vezes, em sentidos opostos."""
    usos = {}
    for a, b, c in tris:
        for u, v in ((a, b), (b, c), (c, a)):
            usos[(u, v)] = usos.get((u, v), 0) + 1
    for (u, v), n in usos.items():
        if n != 1 or usos.get((v, u), 0) != 1:
            return False
    return True


def _volume(verts, tris):
    s = 0.0
    for a, b, c in tris:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = verts[a], verts[b], verts[c]
        s += (x1 * (y2 * z3 - y3 * z2) - x2 * (y1 * z3 - y3 * z1)
              + x3 * (y1 * z2 - y2 * z1))
    return s / 6.0


def agrupar_por_slot(entrada, saida=None, aplicacao="generate-bambu 2 (Fusion)"):
    """Lê o 3MF do Fusion e reescreve com um objeto por slotN.

    entrada: .3mf exportado pelo Fusion. saida: caminho final (padrão: o mesmo).
    Devolve um relatório: unidade, objetos (slot, cor, nº de corpos, nº de
    triângulos, volume, fechada) e avisos. Levanta ValueError se algum corpo
    não tiver prefixo slotN, se houver mais de 4 slots, ou se a unidade não
    for milímetro.
    """
    saida = saida or entrada
    with zipfile.ZipFile(entrada) as z:
        raiz = ET.fromstring(z.read("3D/3dmodel.model"))

    unidade = raiz.get("unit", "millimeter")
    if unidade != "millimeter":
        raise ValueError(f"unidade {unidade!r}: o fluxo exige millimeter")

    cores = _tabela_de_cores(raiz)
    transf = {}
    for it in raiz.iter(f"{{{NS_CORE}}}item"):
        transf[it.get("objectid")] = _matriz(it.get("transform"))

    grupos, sem_slot, avisos = {}, [], []
    for obj in raiz.iter(f"{{{NS_CORE}}}object"):
        malha = obj.find(f"{{{NS_CORE}}}mesh")
        nome = obj.get("name") or f"objeto{obj.get('id')}"
        if malha is None:
            avisos.append(f"{nome}: objeto sem malha (componente) ignorado")
            continue
        m = _RE_SLOT.match(nome)
        if not m:
            sem_slot.append(nome)
            continue
        slot = m.group(1).lower()
        ap = transf.get(obj.get("id"))
        vs = []
        for v in malha.iter(f"{{{NS_CORE}}}vertex"):
            p = (float(v.get("x")), float(v.get("y")), float(v.get("z")))
            vs.append(ap(*p) if ap else p)
        ts = [(int(t.get("v1")), int(t.get("v2")), int(t.get("v3")))
              for t in malha.iter(f"{{{NS_CORE}}}triangle")]
        lista = cores.get(obj.get("pid"), [])
        idx = int(obj.get("pindex") or 0)
        cor = lista[idx] if idx < len(lista) else None
        g = grupos.setdefault(slot, {"verts": [], "tris": [], "cores": set(),
                                     "corpos": []})
        off = len(g["verts"])
        g["verts"].extend(vs)
        g["tris"].extend((a + off, b + off, c + off) for a, b, c in ts)
        if cor:
            g["cores"].add(cor.upper())
        g["corpos"].append(nome)

    if sem_slot:
        raise ValueError("corpos sem prefixo slotN_: " + ", ".join(sem_slot)
                         + " — renomeie no Fusion e exporte de novo")
    if not grupos:
        raise ValueError("nenhum objeto com malha no arquivo")
    if len(grupos) > 4:
        raise ValueError(f"{len(grupos)} slots: o AMS Lite tem 4")

    ordem = sorted(grupos, key=lambda s: int(s[4:]))
    relatorio = []
    partes = ['<?xml version="1.0" encoding="UTF-8"?>',
              f'<model unit="millimeter" xml:lang="en-US" xmlns="{NS_CORE}" '
              f'xmlns:m="{NS_MAT}">',
              f'<metadata name="Application">{escape(aplicacao)}</metadata>',
              '<resources>', '<basematerials id="1">']
    for s in ordem:
        g = grupos[s]
        if len(g["cores"]) > 1:
            avisos.append(f"{s}: corpos com cores diferentes {sorted(g['cores'])}"
                          " — usando a primeira")
        g["cor"] = sorted(g["cores"])[0] if g["cores"] else "#CCCCCCFF"
        if g["cor"] in ("#A0A0A0FF", "#CCCCCCFF"):
            avisos.append(f"{s}: cinza padrão do Fusion — algum corpo ficou sem"
                          " appearance bubble_#rrggbb")
        partes.append(f'<base name="{s}" displaycolor="{g["cor"]}"/>')
    partes.append('</basematerials>')
    # Cor também POR TRIÂNGULO: é o que o Bambu Studio lê num 3MF de terceiro
    # (abre o diálogo "Standard 3mf Import color" e cria os filamentos com as
    # cores certas). Só basematerials no objeto ele ignora — testado.
    partes.append('<m:colorgroup id="100">')
    for s in ordem:
        partes.append(f'<m:color color="{grupos[s]["cor"]}"/>')
    partes.append('</m:colorgroup>')
    for i, s in enumerate(ordem):
        g = grupos[s]
        partes.append(f'<object id="{i + 2}" type="model" pid="1" pindex="{i}" '
                      f'name="{s}">')
        partes.append('<mesh><vertices>')
        partes.extend(f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>'
                      for x, y, z in g["verts"])
        partes.append('</vertices><triangles>')
        partes.extend(f'<triangle v1="{a}" v2="{b}" v3="{c}" pid="100" p1="{i}"/>'
                      for a, b, c in g["tris"])
        partes.append('</triangles></mesh></object>')
        fechada = _conferir_fechada(g["tris"])
        if not fechada:
            avisos.append(f"{s}: malha não fechada — corrija a geometria no Fusion")
        relatorio.append({"slot": s, "cor": g["cor"], "corpos": len(g["corpos"]),
                          "triangulos": len(g["tris"]),
                          "volume_mm3": round(abs(_volume(g["verts"], g["tris"])), 2),
                          "fechada": fechada})
    partes.append('</resources><build>')
    partes.extend(f'<item objectid="{i + 2}"/>' for i in range(len(ordem)))
    partes.append('</build></model>')

    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", "\n".join(partes))

    return {"arquivo": saida, "unidade": "millimeter", "objetos": relatorio,
            "avisos": avisos,
            "tudo_fechado": all(o["fechada"] for o in relatorio)}
