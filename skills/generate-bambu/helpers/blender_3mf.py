"""Roda DENTRO do Blender: prepara a cena, valida e exporta o .3mf da peça.

Mesmo contrato do Fusion: cada cor é um objeto `slotN_descricao`, com material
`cor_#rrggbb`. A cor vem do nome do material, não do valor do nó, para não
passar pela conversão sRGB/linear. A malha é a avaliada, com modificadores aplicados.

Testado no Blender 5.2.3 LTS, com `--background` e sem interface.
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agrupar_3mf import MAX_SLOTS, PREFIXO_COR, RE_COR, RE_SLOT, montar_3mf  # noqa: E402

LIMITE_MM = 250.0
_VOLUME_MINIMO_MM3 = 1e-3


def preparar_cena():
    """Cena vazia em milímetros: 1 unidade do Blender vale 1 mm."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    unidades = bpy.context.scene.unit_settings
    unidades.system = "METRIC"
    unidades.length_unit = "MILLIMETERS"
    unidades.scale_length = 0.001


def colorir(objeto, hexcor):
    nome = PREFIXO_COR + hexcor.lower()
    material = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    r, g, b = (int(hexcor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    material.diffuse_color = (r, g, b, 1)
    objeto.data.materials.clear()
    objeto.data.materials.append(material)


def _malha(objeto):
    """(verts em mm no mundo, triângulos), com modificadores aplicados."""
    grafo = bpy.context.evaluated_depsgraph_get()
    avaliado = objeto.evaluated_get(grafo)
    malha = avaliado.to_mesh()
    malha.calc_loop_triangles()
    escala = bpy.context.scene.unit_settings.scale_length * 1000
    matriz = avaliado.matrix_world
    verts = [tuple(c * escala for c in matriz @ v.co) for v in malha.vertices]
    invertido = matriz.to_3x3().determinant() < 0
    tris = [tuple(reversed(t.vertices)) if invertido else tuple(t.vertices)
            for t in malha.loop_triangles]
    avaliado.to_mesh_clear()
    return verts, tris


def _medir(objeto):
    grafo = bpy.context.evaluated_depsgraph_get()
    avaliado = objeto.evaluated_get(grafo)
    malha = avaliado.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(malha)
    fechada = all(a.is_manifold for a in bm.edges) and all(a.is_contiguous for a in bm.edges)
    bmesh.ops.transform(bm, matrix=avaliado.matrix_world, verts=bm.verts)
    escala = bpy.context.scene.unit_settings.scale_length * 1000
    volume = abs(bm.calc_volume()) * escala ** 3
    bm.free()
    avaliado.to_mesh_clear()
    return fechada, volume


def _objetos():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _slot(nome, max_slots):
    """Número do slot, ou None se o nome fugir do contrato."""
    m = RE_SLOT.match(nome)
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= max_slots else None


def _cor(objeto):
    return RE_COR.match(objeto.active_material.name) if objeto.active_material else None


def _volume_comum(a, b):
    """Volume da interseção: faces só encostadas dão zero, sobreposição dá volume."""
    grafo = bpy.context.evaluated_depsgraph_get()
    malha_a = bpy.data.meshes.new_from_object(a.evaluated_get(grafo))
    copia = bpy.data.objects.new("_comum", malha_a)
    copia.matrix_world = a.matrix_world
    bpy.context.collection.objects.link(copia)
    modificador = copia.modifiers.new("comum", "BOOLEAN")
    modificador.operation = "INTERSECT"
    modificador.object = b
    bpy.context.view_layer.update()
    try:
        return _medir(copia)[1]
    finally:
        malha = copia.data
        bpy.data.objects.remove(copia)
        bpy.data.meshes.remove(malha)


def validar(max_slots=MAX_SLOTS, limite_mm=LIMITE_MM):
    """Mesmas perguntas do passo 1c. Devolve dict com `ok` e a lista `erros`."""
    corpos, erros, slots = {}, [], {}
    objetos = _objetos()
    if not objetos:
        erros.append("cena sem malha")
    for o in objetos:
        slot, cor = _slot(o.name, max_slots), _cor(o)
        fechada, volume = _medir(o)
        corpos[o.name] = {"fechada": fechada, "volume_mm3": round(volume, 2)}
        if slot is None:
            erros.append(f"{o.name}: nome fora do contrato slotN_descricao, N de 1 a {max_slots}")
        if not cor:
            erros.append(f"{o.name}: sem material {PREFIXO_COR}#rrggbb")
        if not fechada:
            erros.append(f"{o.name}: malha aberta ou não-manifold")
        if volume < _VOLUME_MINIMO_MM3:
            erros.append(f"{o.name}: volume zero")
        if slot is not None and cor and slots.setdefault(slot, cor.group(1)) != cor.group(1):
            erros.append(f"slot{slot}: corpos com cores diferentes")

    pontos = [v for o in objetos for v in _malha(o)[0]]
    total = [0.0, 0.0, 0.0]
    if pontos:
        total = [round(max(p[i] for p in pontos) - min(p[i] for p in pontos), 2) for i in range(3)]
    if any(v > limite_mm for v in total):
        erros.append(f"peça de {total} mm não cabe em {limite_mm:.0f} mm")

    interferencias = []
    for i, a in enumerate(objetos):
        for b in objetos[i + 1:]:
            if a.name.split("_")[0] != b.name.split("_")[0]:
                comum = _volume_comum(a, b)
                if comum > _VOLUME_MINIMO_MM3:
                    interferencias.append((a.name, b.name, round(comum, 3)))
    if interferencias:
        erros.append(f"cores sobrepostas: {interferencias}")
    return {"ok": not erros, "erros": erros, "corpos": corpos, "total_mm": total,
            "n_slots": len(slots), "interferencias": interferencias}


def slots_da_cena(max_slots=MAX_SLOTS):
    grupos = {}
    for o in _objetos():
        numero, cor = _slot(o.name, max_slots), _cor(o)
        if numero is None or not cor:
            raise ValueError(f"{o.name}: fora do contrato; rode validar()")
        slot = grupos.setdefault(numero, {
            "slot": f"slot{numero}", "cor": cor.group(1).upper() + "FF",
            "verts": [], "tris": [], "corpos": [],
        })
        verts, tris = _malha(o)
        base = len(slot["verts"])
        slot["verts"].extend(verts)
        slot["tris"].extend(tuple(i + base for i in t) for t in tris)
        slot["corpos"].append(o.name)
    return [grupos[n] for n in sorted(grupos)]


def salvar(caminho):
    bpy.ops.wm.save_as_mainfile(filepath=str(caminho))


def exportar(caminho, max_slots=MAX_SLOTS, limite_mm=LIMITE_MM):
    """Grava o .3mf da peça, recusando cena que não passa na validação."""
    resultado = validar(max_slots, limite_mm)
    if not resultado["ok"]:
        raise ValueError("; ".join(resultado["erros"]))
    return montar_3mf(slots_da_cena(max_slots), str(caminho), max_slots=max_slots)


def imprimir_json(dados):
    print("RESULTADO " + json.dumps(dados, ensure_ascii=False))
