"""Leitura do 3MF fatiado pelo Bambu Studio.

O Bambu Studio grava o resultado do fatiamento dentro do próprio 3MF
(`Metadata/slice_info.config`): tempo previsto, peso e gramas por filamento. A
estimativa é tomada como verdade, sem recálculo. Um projeto salvo sem fatiar não
tem `<plate>` nesse arquivo. Só a primeira placa é lida: a skill gera uma por peça.

Stdlib pura.
"""

import json
import re
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree

SLICE_INFO = "Metadata/slice_info.config"
PROJECT_SETTINGS = "Metadata/project_settings.config"
# A1 sem torre de purga não faz timelapse tradicional: aviso sem efeito na peça.
AVISOS_IGNORADOS = {"not_support_traditional_timelapse"}
_RE_HEX = re.compile(r"^#?([0-9a-fA-F]{6})(?:[0-9a-fA-F]{2})?$")


class Erro3mf(ValueError):
    """O arquivo não é um 3MF legível do Bambu Studio."""


@dataclass(frozen=True)
class FilamentoFatiado:
    slot: int
    material: str
    cor_hex: str
    usado_g: float
    usado_m: float


@dataclass(frozen=True)
class Resumo3mf:
    fatiado: bool
    tempo_estimado_s: int | None = None
    peso_g: float | None = None
    camadas_total: int | None = None
    camada_mm: float | None = None
    filamentos: tuple = ()
    avisos: tuple = ()


def normalizar_hex(valor):
    """#RRGGBB ou #RRGGBBAA, com ou sem #, vira #RRGGBB maiúsculo."""
    achado = _RE_HEX.match((valor or "").strip())
    if not achado:
        raise ValueError(f"cor inválida: {valor!r}")
    return "#" + achado.group(1).upper()


def _numero(valor):
    try:
        return float(valor or 0)
    except ValueError as erro:
        raise Erro3mf(f"Valor numérico inválido no slice_info do 3mf: {valor!r}") from erro


def _parse(bruto):
    # 3MF vem de arquivo do usuário: recusa DTD/entidades (expansão de entidades).
    if b"<!DOCTYPE" in bruto or b"<!ENTITY" in bruto:
        raise Erro3mf("slice_info do 3mf com DTD/entidades não é aceito.")
    try:
        return ElementTree.fromstring(bruto)
    except ElementTree.ParseError as erro:
        raise Erro3mf(f"slice_info do 3mf está corrompido: {erro}") from erro


def _camadas(plate):
    """Camadas = maior índice em `layer_ranges` + 1 (os índices começam em 0)."""
    indices = []
    for lista in plate.iter("layer_filament_list"):
        indices += [int(n) for n in (lista.get("layer_ranges") or "").split() if n.isdigit()]
    return max(indices) + 1 if indices else None


def _filamentos(plate):
    filamentos = []
    for f in plate.findall("filament"):
        try:
            filamentos.append(FilamentoFatiado(
                slot=int(f.get("id", "")),
                material=(f.get("type") or "").strip().upper(),
                cor_hex=normalizar_hex(f.get("color", "")),
                usado_g=_numero(f.get("used_g")),
                usado_m=_numero(f.get("used_m")),
            ))
        except ValueError as erro:
            raise Erro3mf(f"Filamento inválido no slice_info do 3mf: {erro}") from erro
    return tuple(filamentos)


def _camada_mm(z):
    if PROJECT_SETTINGS not in z.namelist():
        return None
    try:
        return float(json.loads(z.read(PROJECT_SETTINGS))["layer_height"])
    except (KeyError, TypeError, ValueError) as erro:
        raise Erro3mf(f"project_settings.config do 3mf está corrompido: {erro}") from erro


def ler_3mf(caminho):
    try:
        with zipfile.ZipFile(caminho) as z:
            if SLICE_INFO not in z.namelist():
                return Resumo3mf(fatiado=False)
            plate = _parse(z.read(SLICE_INFO)).find("plate")
            filamentos = _filamentos(plate) if plate is not None else ()
            if not filamentos:
                return Resumo3mf(fatiado=False)
            meta = {m.get("key", ""): m.get("value", "") for m in plate.findall("metadata")}
            avisos = tuple(dict.fromkeys(
                w.get("msg", "") for w in plate.findall("warning")
                if w.get("msg") not in AVISOS_IGNORADOS
            ))
            return Resumo3mf(
                fatiado=True,
                tempo_estimado_s=int(_numero(meta["prediction"])) if "prediction" in meta else None,
                peso_g=_numero(meta["weight"]) if "weight" in meta else None,
                camadas_total=_camadas(plate),
                camada_mm=_camada_mm(z),
                filamentos=filamentos,
                avisos=avisos,
            )
    except (OSError, zipfile.BadZipFile) as erro:
        raise Erro3mf(f"Não foi possível abrir o arquivo 3mf {caminho}: {erro}") from erro
