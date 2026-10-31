r"""Receitas de blender-api.md contra o Blender de verdade (opt-in).

    BLENDER_EXE=D:\Blender\blender.exe

Roda com --background, sem janela. Com BAMBU_STUDIO_EXE definida, também fatia no
computador. Nada aqui fala com a impressora.
"""

import json
import os
import subprocess
from pathlib import Path

import config as cfg
import fatiar as ft
import pytest
from conftest import SKILL

EXE = os.environ.get("BLENDER_EXE")
BAMBU = os.environ.get("BAMBU_STUDIO_EXE")

pytestmark = pytest.mark.skipif(
    not (EXE and Path(EXE).is_file()),
    reason="defina BLENDER_EXE para rodar contra o Blender real",
)

CABECALHO = f"""
import sys
sys.path.insert(0, {str(SKILL / "helpers")!r})
import bmesh, bpy
from mathutils import Matrix
import blender_3mf as b

CAMADA = 0.12

def caixa(nome, x, y, z, cor, sx=10, sy=10, sz=2):
    malha = bpy.data.meshes.new(nome)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(x, y, z + sz / 2), verts=bm.verts)
    bm.to_mesh(malha)
    bm.free()
    o = bpy.data.objects.new(nome, malha)
    bpy.context.collection.objects.link(o)
    b.colorir(o, cor)
    return o

def esfera(nome, raio, centro, cor, escala=(1, 1, 1), sub=3):
    malha = bpy.data.meshes.new(nome)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=raio,
                               matrix=Matrix.Translation(centro) @ Matrix.Diagonal((*escala, 1)))
    bm.to_mesh(malha)
    bm.free()
    o = bpy.data.objects.new(nome, malha)
    bpy.context.collection.objects.link(o)
    b.colorir(o, cor)
    return o

b.preparar_cena()
"""


def rodar(tmp_path, corpo):
    script = tmp_path / "peca.py"
    script.write_text(CABECALHO + corpo, encoding="utf-8")
    r = subprocess.run(
        [EXE, "--background", "--factory-startup", "--python-exit-code", "1",
         "--python", str(script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    linhas = [li for li in r.stdout.splitlines() if li.startswith("RESULTADO ")]
    assert r.returncode == 0 and linhas, r.stdout[-1500:] + r.stderr[-1500:]
    return json.loads(linhas[-1][len("RESULTADO "):])


def test_faces_encostadas_passam(tmp_path):
    r = rodar(tmp_path, """
caixa("slot1_base", 0, 0, 0, "#e8b647")
caixa("slot2_relevo", 0, 0, 2, "#1a73e8", 5, 5, 1)
b.imprimir_json(b.validar())
""")

    assert r["ok"], r
    assert r["total_mm"] == [10, 10, 3]
    assert r["n_slots"] == 2


def test_cores_sobrepostas_falham(tmp_path):
    r = rodar(tmp_path, """
caixa("slot1_base", 0, 0, 0, "#e8b647")
caixa("slot2_relevo", 0, 0, 1, "#1a73e8", 5, 5, 2)
b.imprimir_json(b.validar())
""")

    assert not r["ok"]
    assert r["interferencias"][0][2] == pytest.approx(25, abs=0.1)


def test_mesmo_slot_pode_sobrepor(tmp_path):
    r = rodar(tmp_path, """
caixa("slot1_a", 0, 0, 0, "#e8b647")
caixa("slot1_b", 2, 0, 0, "#e8b647")
b.imprimir_json(b.validar())
""")

    assert r["interferencias"] == []


@pytest.mark.parametrize(
    "corpo, erro",
    [
        ('caixa("cubo", 0, 0, 0, "#e8b647")', "contrato"),
        ('caixa("slot5_x", 0, 0, 0, "#e8b647")', "contrato"),
        ('o = caixa("slot1_x", 0, 0, 0, "#e8b647"); o.data.materials.clear()', "cor_"),
        ('caixa("slot1_x", 0, 0, 0, "#e8b647", 300, 10, 2)', "não cabe"),
        ('o = caixa("slot1_x", 0, 0, 0, "#e8b647"); bm = bmesh.new(); bm.from_mesh(o.data); '
         'bmesh.ops.delete(bm, geom=list(bm.faces)[:1], context="FACES_ONLY"); '
         'bm.to_mesh(o.data); bm.free()', "não-manifold"),
    ],
)
def test_validacao_recusa(tmp_path, corpo, erro):
    r = rodar(tmp_path, corpo + "\nb.imprimir_json(b.validar())\n")

    assert not r["ok"]
    assert any(erro in e for e in r["erros"]), r["erros"]


def test_exportar_recusa_cena_invalida(tmp_path):
    r = rodar(tmp_path, """
caixa("cubo", 0, 0, 0, "#e8b647")
try:
    b.exportar(r"X")
except ValueError as e:
    b.imprimir_json(str(e))
""")

    assert "contrato" in r


def test_modificador_entra_na_malha_exportada(tmp_path):
    saida = tmp_path / "m.3mf"
    r = rodar(tmp_path, f"""
o = caixa("slot1_x", 0, 0, 0, "#e8b647")
o.modifiers.new("s", "BEVEL")
b.imprimir_json(b.exportar(r"{saida}"))
""")

    assert r["objetos"][0]["triangulos"] > 12
    assert r["tudo_fechado"]


def test_bicho_low_poly_ate_o_fatiado(tmp_path):
    """Organico de 2 cores: olho encaixado no corpo por booleana."""
    saida = tmp_path / "bicho.3mf"
    blend = tmp_path / "bicho.blend"
    r = rodar(tmp_path, f"""
corpo = esfera("slot1_corpo", 15, (0, 0, 15), "#e8b647", (1, .8, 1))
cabeca = esfera("slot1_cabeca", 9, (12, 0, 25), "#e8b647")
corta = corpo.modifiers.new("chao", "BOOLEAN")
olhos = [esfera(f"slot2_olho_{{i}}", 2, (19, s * 4, 27), "#222222", sub=2)
         for i, s in enumerate((-1, 1))]
for fonte in olhos:
    m = cabeca.modifiers.new(fonte.name, "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.object = fonte
corpo.modifiers.remove(corta)
m = corpo.modifiers.new("cabeca", "BOOLEAN")
m.operation = "DIFFERENCE"
m.object = cabeca
bpy.context.view_layer.update()
v = b.validar()
b.salvar(r"{blend}")
b.imprimir_json({{"validacao": v, "exportado": b.exportar(r"{saida}")}})
""")

    assert r["validacao"]["ok"], r["validacao"]["erros"]
    assert r["exportado"]["tudo_fechado"]
    assert blend.is_file()
    if not (BAMBU and Path(BAMBU).is_file()):
        return
    config = json.loads(json.dumps(cfg.PADRAO))
    fatiado = ft.processar(saida, config, {"exe": BAMBU, "versao": None})
    assert [f["slot"] for f in fatiado["filamentos"]] == ["slot1", "slot2"]
    assert all(f["g"] > 0 for f in fatiado["filamentos"])
