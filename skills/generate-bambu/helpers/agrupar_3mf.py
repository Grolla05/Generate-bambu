"""Agrupa os objetos de um .3mf exportado pelo Fusion: um objeto por slot do AMS.

Por que existe: o Fusion exporta um <object> por corpo. Texto extrudado vira
um corpo por letra, e corpos que não se tocam não podem ser unidos com Combine.
Sem agrupar, "BUBBLE" chega ao Bambu Studio como 6 objetos, e cada letra
pede um clique de filamento.

Regra de agrupamento: o nome do corpo começa com "slotN_", com N de 1 a 4
(slot1_base, slot3_texto_B...). Todos os corpos com o mesmo "slotN" viram um
objeto só, com várias cascas (shells) — válido em 3MF e lido normalmente pelo
slicer. Corpo sem prefixo slotN_ é recusado: nome de corpo é contrato do fluxo.

Cor: grava basematerials por objeto e colorgroup por triângulo — o Bambu
Studio só reconhece a segunda forma em 3MF que não foi feito por ele.

Duas metades: ler_slots_fusion() entende o arquivo do Fusion e montar_3mf()
grava um 3MF a partir de slots, venha a malha de onde vier.

Stdlib pura. Roda DENTRO do Fusion: cole este arquivo inteiro no começo do
script do passo 3 e chame agrupar_por_slot(). Também roda fora do Fusion.
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

NS_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_MAT = "http://schemas.microsoft.com/3dmanufacturing/material/2015/02"
APLICACAO = "generate-bambu 3.0.0"
_RE_SLOT = re.compile(r"^slot(\d+)_", re.IGNORECASE)
_RE_SLOT_AGRUPADO = re.compile(r"^slot(\d+)(?:_|$)", re.IGNORECASE)

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


def ler_slots_fusion(entrada, agrupado=False):
    """Lê o 3MF do Fusion e agrupa as malhas por slot.

    Devolve (slots, avisos). Cada slot é um dict com slot ("slot1"), cor, verts,
    tris e corpos, em ordem de N. Levanta ValueError se algum corpo não tiver
    prefixo slotN_, se N sair de 1 a 4, ou se a unidade não for milímetro.
    agrupado=True lê um arquivo que já passou por aqui: lá o nome é só "slotN".
    """
    padrao = _RE_SLOT_AGRUPADO if agrupado else _RE_SLOT
    with zipfile.ZipFile(entrada) as z:
        raiz = ET.fromstring(z.read("3D/3dmodel.model"))

    unidade = raiz.get("unit", "millimeter")
    if unidade != "millimeter":
        raise ValueError(f"unidade {unidade!r}: o fluxo exige millimeter")

    cores = _tabela_de_cores(raiz)
    transf = {}
    for it in raiz.iter(f"{{{NS_CORE}}}item"):
        transf[it.get("objectid")] = _matriz(it.get("transform"))

    grupos, sem_slot, fora, avisos = {}, [], [], []
    for obj in raiz.iter(f"{{{NS_CORE}}}object"):
        malha = obj.find(f"{{{NS_CORE}}}mesh")
        nome = obj.get("name") or f"objeto{obj.get('id')}"
        if malha is None:
            avisos.append(f"{nome}: objeto sem malha (componente) ignorado")
            continue
        m = padrao.match(nome)
        if not m:
            sem_slot.append(nome)
            continue
        if not 1 <= int(m.group(1)) <= 4:
            fora.append(nome)
            continue
        slot = f"slot{int(m.group(1))}"
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
    if fora:
        raise ValueError("slot fora de 1 a 4: " + ", ".join(fora) + " — o AMS Lite tem 4")
    if not grupos:
        raise ValueError("nenhum objeto com malha no arquivo")

    slots = []
    for s in sorted(grupos, key=lambda n: int(n[4:])):
        g = grupos[s]
        if len(g["cores"]) > 1:
            avisos.append(f"{s}: corpos com cores diferentes {sorted(g['cores'])}"
                          " — usando a primeira")
        cor = sorted(g["cores"])[0] if g["cores"] else None
        slots.append({"slot": s, "cor": cor, "verts": g["verts"], "tris": g["tris"],
                      "corpos": g["corpos"]})
    return slots, avisos


def montar_3mf(slots, saida, aplicacao=APLICACAO, avisos=()):
    """Grava um 3MF com um objeto por slot e devolve o relatório.

    slots: lista de dicts com slot, cor (#RRGGBBAA ou None), verts, tris e corpos,
    como devolve ler_slots_fusion(). avisos entra no relatório, que traz unidade,
    objetos (slot, cor, nº de corpos, nº de triângulos, volume, fechada) e avisos.
    """
    avisos = list(avisos)
    if not slots:
        raise ValueError("nenhum slot para gravar")
    if len(slots) > 4:
        raise ValueError(f"{len(slots)} slots: o AMS Lite tem 4")

    relatorio = []
    partes = ['<?xml version="1.0" encoding="UTF-8"?>',
              f'<model unit="millimeter" xml:lang="en-US" xmlns="{NS_CORE}" '
              f'xmlns:m="{NS_MAT}">',
              f'<metadata name="Application">{escape(aplicacao)}</metadata>',
              '<resources>', '<basematerials id="1">']
    cores = [s["cor"] or "#CCCCCCFF" for s in slots]
    for s, cor in zip(slots, cores, strict=True):
        if cor in ("#A0A0A0FF", "#CCCCCCFF"):
            avisos.append(f"{s['slot']}: cinza padrão — algum corpo ficou sem"
                          " cor bubble_#rrggbb")
        partes.append(f'<base name="{s["slot"]}" displaycolor="{cor}"/>')
    partes.append('</basematerials>')
    # Cor também POR TRIÂNGULO: é o que o Bambu Studio lê num 3MF de terceiro
    # (abre o diálogo "Standard 3mf Import color" e cria os filamentos com as
    # cores certas). Só basematerials no objeto ele ignora — testado.
    partes.append('<m:colorgroup id="100">')
    partes.extend(f'<m:color color="{cor}"/>' for cor in cores)
    partes.append('</m:colorgroup>')
    for i, s in enumerate(slots):
        partes.append(f'<object id="{i + 2}" type="model" pid="1" pindex="{i}" '
                      f'name="{s["slot"]}">')
        partes.append('<mesh><vertices>')
        partes.extend(f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>'
                      for x, y, z in s["verts"])
        partes.append('</vertices><triangles>')
        partes.extend(f'<triangle v1="{a}" v2="{b}" v3="{c}" pid="100" p1="{i}"/>'
                      for a, b, c in s["tris"])
        partes.append('</triangles></mesh></object>')
        fechada = _conferir_fechada(s["tris"])
        if not fechada:
            avisos.append(f"{s['slot']}: malha não fechada — corrija a geometria no modelador")
        relatorio.append({"slot": s["slot"], "cor": cores[i], "corpos": len(s["corpos"]),
                          "triangulos": len(s["tris"]),
                          "volume_mm3": round(abs(_volume(s["verts"], s["tris"])), 2),
                          "fechada": fechada})
    partes.append('</resources><build>')
    partes.extend(f'<item objectid="{i + 2}"/>' for i in range(len(slots)))
    partes.append('</build></model>')

    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", "\n".join(partes))

    return {"arquivo": saida, "unidade": "millimeter", "objetos": relatorio,
            "avisos": avisos,
            "tudo_fechado": all(o["fechada"] for o in relatorio)}


def agrupar_por_slot(entrada, saida=None, aplicacao=APLICACAO):
    """Lê o 3MF do Fusion e reescreve com um objeto por slotN.

    entrada: .3mf exportado pelo Fusion. saida: caminho final (padrão: o mesmo).
    Devolve o relatório de montar_3mf(). Levanta ValueError nos casos de
    ler_slots_fusion() e com mais de 4 slots.
    """
    slots, avisos = ler_slots_fusion(entrada)
    return montar_3mf(slots, saida or entrada, aplicacao, avisos)
