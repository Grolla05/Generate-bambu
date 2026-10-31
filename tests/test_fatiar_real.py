r"""Fatiamento contra o Bambu Studio de verdade (opt-in).

Roda só com BAMBU_STUDIO_EXE definida, porque depende do programa instalado:

    BAMBU_STUDIO_EXE=D:\Bambu Studio\bambu-studio.exe

Só fatia no computador: não abre a interface e não fala com a impressora.
"""

import json
import os
import zipfile
from pathlib import Path

import config as cfg
import fatiar as ft
import pytest
from agrupar_3mf import montar_3mf

EXE = os.environ.get("BAMBU_STUDIO_EXE")
CAMADA = 0.12

pytestmark = pytest.mark.skipif(
    not (EXE and Path(EXE).is_file()),
    reason="defina BAMBU_STUDIO_EXE para rodar contra o Bambu Studio real",
)


def _caixa(x0, y0, z0, x1, y1, z1):
    v = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    t = [(0, 2, 3), (0, 3, 1), (4, 5, 7), (4, 7, 6), (0, 1, 5), (0, 5, 4),
         (2, 6, 7), (2, 7, 3), (0, 4, 6), (0, 6, 2), (1, 3, 7), (1, 7, 5)]
    return v, t


def _slot(n, cor, *caixas):
    verts, tris = [], []
    for v, t in caixas:
        o = len(verts)
        verts += v
        tris += [(a + o, b + o, c + o) for a, b, c in t]
    return {"slot": f"slot{n}", "cor": cor, "verts": verts, "tris": tris, "corpos": ["a"]}


def _fatiar(tmp_path, slots, nome="peca"):
    entrada = tmp_path / f"{nome}.3mf"
    montar_3mf(slots, str(entrada))
    config = json.loads(json.dumps(cfg.PADRAO))
    return ft.processar(entrada, config, {"exe": EXE, "versao": None})


def test_tres_cores_com_relevo_e_duas_cascas(tmp_path):
    z1, z2 = 17 * CAMADA, 24 * CAMADA
    slots = [
        _slot(1, "#E8B647FF", _caixa(-30, -15, 0, 30, 15, z1)),
        _slot(2, "#1A73E8FF", _caixa(-24, -12, z1, -3, 12, z2)),
        _slot(3, "#D93025FF", _caixa(3, -7, z1, 12, 7, z2), _caixa(15, -7, z1, 24, 7, z2)),
    ]

    r = _fatiar(tmp_path, slots)

    assert r["camada_mm"] == CAMADA
    assert r["dimensoes_mm"] == pytest.approx([60, 30, z2], abs=0.05)
    assert [f["slot"] for f in r["filamentos"]] == ["slot1", "slot2", "slot3"]
    assert all(f["g"] > 0 for f in r["filamentos"])
    assert [f["cor"] for f in r["filamentos"]] == ["#E8B647", "#1A73E8", "#D93025"]
    assert r["tempo_s"] > 0
    with zipfile.ZipFile(r["arquivo"]) as z:
        gcode = z.read("Metadata/plate_1.gcode").decode(errors="replace")
    # relevo sobre a base e alturas em múltiplos da camada: o último Z é o topo exato
    assert f"; Z_HEIGHT: {z2:.2f}" in gcode


def test_uma_cor(tmp_path):
    r = _fatiar(tmp_path, [_slot(1, "#E8B647FF", _caixa(-20, -10, 0, 20, 10, 25 * CAMADA))])

    assert len(r["filamentos"]) == 1
    assert r["avisos"] == []


def test_multicor_grande_sai_de_perto_da_torre(tmp_path):
    z1 = 10 * CAMADA
    slots = [
        _slot(1, "#E8B647FF", _caixa(-85, -85, 0, 85, 85, z1)),
        _slot(2, "#1A73E8FF", _caixa(-40, -40, z1, 40, 40, z1 + 4 * CAMADA)),
    ]

    assert _fatiar(tmp_path, slots)["dimensoes_mm"][:2] == pytest.approx([170, 170], abs=0.05)


def test_quatro_cores_altas_descem_a_torre(tmp_path):
    h = 334 * CAMADA
    cores = ["#E8B647FF", "#1A73E8FF", "#D93025FF", "#222222FF"]
    slots = [_slot(i + 1, c, _caixa(-30 + i * 15, -7, 0, -16 + i * 15, 7, h))
             for i, c in enumerate(cores)]

    assert len(_fatiar(tmp_path, slots)["filamentos"]) == 4


def test_multicor_que_nao_deixa_lugar_para_a_torre(tmp_path):
    slots = [
        _slot(1, "#E8B647FF", _caixa(-100, -100, 0, 100, 100, 1.2)),
        _slot(2, "#1A73E8FF", _caixa(-40, -40, 1.2, 40, 40, 1.68)),
    ]

    with pytest.raises(ValueError, match="torre de purga"):
        _fatiar(tmp_path, slots)
