"""Monta o `project_settings.config` a partir dos perfis do Bambu Studio instalado.

Os arquivos de resources/profiles/BBL são parciais (`inherits` e `include`), e sem
esta configuração completa o CLI cai com access violation num 3MF sem projeto. Lê do
programa instalado, em vez de copiar perfis para cá, porque eles são AGPL.

Conferido com o Bambu Studio 02.08.03.66 (a interface recusa o projeto com "Invalid
configuration file" se algum vetor não tiver um valor por filamento). A matriz de
purga fica de fora de propósito: o CLI calcula pelas cores.

Stdlib pura.
"""

import json
from pathlib import Path

VERSAO_TESTADA = "02.08.03.66"
# Chave do perfil de filamento que não é vetor por filamento.
_NAO_VETOR = {
    "type", "name", "inherits", "from", "setting_id", "instantiation", "description",
    "compatible_printers", "compatible_printers_condition", "filament_id",
    "is_custom_defined", "include",
}
# Campos do perfil que não existem na configuração do projeto.
_FORA_DO_PROJETO = {
    "type", "name", "inherits", "include", "setting_id", "instantiation", "description",
    "is_custom_defined", "compatible_printers", "compatible_printers_condition",
    "adaptive_layer_height", "extruder_clearance_radius", "extruder_height_gap",
    "filament_contact_safe", "filament_emission_safe", "filament_ingredients_safe",
    "filament_long_retractions_when_ec", "filament_retraction_distances_when_ec",
    "layer_time_smoothing", "layer_time_smoothing_threshold", "only_one_wall_top",
    "wall_infill_order",
}
# Vetores por filamento que nenhum perfil traz; sem eles o CLI grava um valor só.
_VETORES_DO_PROJETO = {
    "default_filament_colour": "",
    "enable_overhang_bridge_fan": "1",
    "enable_pressure_advance": "0",
    "filament_change_length_nc": "10",
    "filament_is_mixed": "0",
    "filament_map": "1",
    "filament_mixed_components": "",
    "filament_mixed_gradient": "0",
    "filament_mixed_gradient_curve": "",
    "filament_mixed_gradient_per_part": "0",
    "filament_mixed_gradient_range": "",
    "filament_mixed_sublayer_ratios": "",
    "filament_nozzle_map": "0",
    "filament_volume_map": "0",
    "first_x_layer_fan_speed": "0",
    "first_x_layer_part_fan_speed": "0",
    "ironing_fan_speed": "-1",
    "overhang_threshold_participating_cooling": "95%",
    "pressure_advance": "0.02",
}


class ErroPerfil(ValueError):
    """Perfil pedido não existe na instalação do Bambu Studio."""


def pasta_perfis(exe):
    return Path(exe).parent / "resources" / "profiles" / "BBL"


def _indice(pasta, tipo):
    indice = {}
    for arquivo in (pasta / tipo).rglob("*.json"):
        try:
            indice[json.loads(arquivo.read_text(encoding="utf-8"))["name"]] = arquivo
        except (KeyError, TypeError, ValueError):
            continue
    return indice


def resolver(pasta, tipo, nome, indice=None):
    """Perfil completo: herança primeiro, depois `include`, e o próprio arquivo por cima."""
    indice = _indice(pasta, tipo) if indice is None else indice
    if nome not in indice:
        raise ErroPerfil(f"perfil de {tipo} não encontrado: {nome}")
    dados = json.loads(indice[nome].read_text(encoding="utf-8"))
    completo = {}
    if dados.get("inherits"):
        completo = resolver(pasta, tipo, dados["inherits"], indice)
    for incluido in dados.get("include") or []:
        completo.update(resolver(pasta, tipo, incluido, indice))
    completo.update(dados)
    return completo


def _vetores_de_filamento(filamentos):
    vetores = {}
    for chave in sorted(set().union(*filamentos) - _NAO_VETOR):
        valores = []
        for filamento in filamentos:
            valor = filamento.get(chave)
            if valor is not None:
                valores += valor if isinstance(valor, list) else [valor]
        vetores[chave] = valores
    return vetores


def config_projeto(pasta, bambu, cores, versao, y_torre):
    """Config do projeto para N filamentos. `bambu` é a seção bambu_studio da configuração."""
    impressora, processo = bambu["impressora"], bambu["processo"]
    filamento = resolver(pasta, "filament", bambu["filamento_padrao"])
    n = len(cores)
    config = {
        **resolver(pasta, "machine", impressora),
        **resolver(pasta, "process", processo),
        **_vetores_de_filamento([filamento] * n),
    }
    for chave in _FORA_DO_PROJETO:
        config.pop(chave, None)
    config.update({k: [v] * n for k, v in _VETORES_DO_PROJETO.items()})
    camada = float(config["layer_height"])
    config.update({
        # Sem isto a primeira camada do perfil fura a regra de alturas em múltiplos da camada.
        "initial_layer_print_height": f"{2 * camada:.2f}",
        "from": "project",
        "name": "project_settings",
        "version": versao,
        "printer_settings_id": impressora,
        "print_settings_id": processo,
        "print_compatible_printers": [impressora],
        "curr_bed_type": bambu["mesa"],
        "filament_settings_id": [bambu["filamento_padrao"]] * n,
        "filament_ids": [filamento.get("filament_id", "")] * n,
        "filament_colour": list(cores),
        "filament_self_index": [str(i + 1) for i in range(n)],
        "flush_volumes_vector": ["140", "140"] * n,
        "extruder_ams_count": ["1#0|4#0", "1#0|4#0"],
        "extruder_nozzle_stats": ["Standard#1"],
        "inherits_group": [""] * (n + 2),
        "different_settings_to_system": [""] * (n + 2),
        "wipe_tower_x": ["15", "15"],
        "wipe_tower_y": [str(y_torre)] * 2,
    })
    return config
