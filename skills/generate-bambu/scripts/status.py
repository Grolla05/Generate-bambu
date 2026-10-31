"""Estado da impressora pela LAN. SÓ LEITURA.

    python status.py                      foto do estado e sai
    python status.py --acompanhar         fica ouvindo e imprime cada mudança de fase
    python status.py --conferir <fatiado> compara os slots da peça com o que está no AMS

Conecta em 8883 com o usuário `bblp`, assina `device/<serial>/report` e pede o estado
completo (`pushall`) uma vez. É o único comando publicado: este script não sabe iniciar,
pausar nem cancelar impressão. Só rode com pedido do usuário.

Exige paho-mqtt (`pip install -r requirements-lan.txt`). O resto é stdlib. Protocolo
conferido numa A1 real com AMS Lite: a A1 só manda deltas em `print.*`, e o estado
completo vem na resposta ao `pushall`.
"""

import argparse
import json
import ssl
import sys
import threading
import zipfile
from xml.etree import ElementTree

import bambu_3mf
import config as cfg

PORTA = 8883
USUARIO = "bblp"
TIMEOUT_S = 15.0
PUSHALL = {"pushing": {"sequence_id": "0", "command": "pushall", "version": 1, "push_target": 1}}
SLOTS_POR_UNIDADE = 4
NENHUMA = 255
FASES_ATIVAS = {"PREPARE", "RUNNING", "PAUSE"}
COR_NULA = "00000000"
DISTANCIA_COR = 120


class ErroStatus(RuntimeError):
    """Sem como ler a impressora; a mensagem diz o que falta."""


def _inteiro(valor):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _cor(valor):
    texto = str(valor or "").strip().upper()
    if not texto or texto == COR_NULA:
        return None
    try:
        return bambu_3mf.normalizar_hex(texto)
    except ValueError:
        return None


def _bits(valor):
    try:
        return int(str(valor), 16)
    except (TypeError, ValueError):
        return None


class Acumulador:
    """Junta os relatórios parciais num estado completo."""

    def __init__(self):
        self.bruto = {}

    def aplicar(self, mensagem):
        delta = mensagem.get("print")
        if not isinstance(delta, dict):
            return
        for chave, valor in delta.items():
            antigo = self.bruto.get(chave)
            if chave == "ams" and isinstance(antigo, dict) and isinstance(valor, dict):
                valor = {**antigo, **valor}  # `ams` parcial não apaga as bandejas
            self.bruto[chave] = valor

    def _bandejas(self):
        ams = self.bruto.get("ams")
        if not isinstance(ams, dict):
            return []
        existe = _bits(ams.get("tray_exist_bits"))
        ativa = _inteiro(ams.get("tray_now"))
        bandejas = []
        for unidade in ams.get("ams") or []:
            base = (_inteiro(unidade.get("id")) or 0) * SLOTS_POR_UNIDADE
            for tray in unidade.get("tray") or []:
                slot = base + (_inteiro(tray.get("id")) or 0)
                material = str(tray.get("tray_type") or "").strip()
                presente = existe is None or bool(existe >> slot & 1)
                vazia = not presente or not material
                bandejas.append({
                    "slot": slot + 1,
                    "material": material,
                    "cor": None if vazia and not material else _cor(tray.get("tray_color")),
                    "em_uso": slot == ativa and ativa != NENHUMA,
                    "vazia": vazia,
                })
        return bandejas

    def estado(self):
        b = self.bruto
        return {
            "fase": b.get("gcode_state"),
            "ativa": b.get("gcode_state") in FASES_ATIVAS,
            "percentual": _inteiro(b.get("mc_percent")),
            "camada": _inteiro(b.get("layer_num")),
            "camadas_total": _inteiro(b.get("total_layer_num")),
            "restante_min": _inteiro(b.get("mc_remaining_time")),
            "tarefa": str(b.get("subtask_name") or ""),
            "erro": _inteiro(b.get("print_error")) or 0,
            "bico": _numero(b.get("nozzle_temper")),
            "mesa": _numero(b.get("bed_temper")),
            "bandejas": self._bandejas(),
        }


def _distancia(a, b):
    return sum(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) for i in (1, 3, 5))


def conferir_ams(bandejas, slots):
    """Avisos do que não bate. slots: [{"slot": 1, "material": "PLA", "cor": "#RRGGBB"}]."""
    por_slot = {b["slot"]: b for b in bandejas}
    avisos = []
    for s in slots:
        bandeja = por_slot.get(s["slot"])
        if bandeja is None or bandeja["vazia"]:
            avisos.append(f"slot{s['slot']}: bandeja vazia; a peça pede {s['material']} {s['cor']}")
            continue
        if bandeja["material"].casefold() != s["material"].casefold():
            avisos.append(f"slot{s['slot']}: {bandeja['material']} na bandeja; "
                          f"a peça pede {s['material']}")
        if bandeja["cor"] and _distancia(bandeja["cor"], s["cor"]) > DISTANCIA_COR:
            avisos.append(f"slot{s['slot']}: cor {bandeja['cor']} na bandeja; "
                          f"a peça pede {s['cor']}")
    return avisos


def slots_do_fatiado(caminho):
    """Lê as partes `slotN` e as cores. O filamento i do projeto é a parte de extruder i."""
    resumo = bambu_3mf.ler_3mf(caminho)
    if not resumo.fatiado:
        raise ErroStatus(f"{caminho} não está fatiado.")
    with zipfile.ZipFile(caminho) as z:
        ajustes = z.read("Metadata/model_settings.config").decode("utf-8", "replace")
    if "<!DOCTYPE" in ajustes or "<!ENTITY" in ajustes:
        raise ErroStatus("model_settings do 3mf com DTD/entidades não é aceito.")
    por_extruder = {}
    for parte in ElementTree.fromstring(ajustes).iter("part"):
        meta = {m.get("key"): m.get("value") for m in parte.findall("metadata")}
        if meta.get("extruder") and (meta.get("name") or "").startswith("slot"):
            por_extruder[int(meta["extruder"])] = int(meta["name"][4:])
    return [{"slot": por_extruder.get(f.slot, f.slot), "material": f.material, "cor": f.cor_hex}
            for f in resumo.filamentos]


def _paho():
    try:
        import paho.mqtt.client as mqtt
        from paho.mqtt.enums import CallbackAPIVersion
    except ImportError as erro:
        raise ErroStatus("Falta o paho-mqtt: pip install -r requirements-lan.txt") from erro
    return mqtt.Client(CallbackAPIVersion.VERSION2)


def credenciais(config, codigo):
    faltam = [n for n, v in (("impressora.host", config["impressora"]["host"]),
                             ("impressora.serial", config["impressora"]["serial"]),
                             ("access code", codigo)) if not v]
    if faltam:
        raise ErroStatus("Falta configurar: " + ", ".join(faltam))
    return config["impressora"]["host"], config["impressora"]["serial"], codigo


def ler(host, serial, codigo, *, acompanhar=None, timeout=TIMEOUT_S, fabrica=_paho):
    """Conecta, pede o estado e devolve. Com `acompanhar`, chama-o a cada mudança de fase."""
    acumulador = Acumulador()
    pronto, recusado = threading.Event(), {}
    fase_vista = {}
    relatorio = f"device/{serial}/report"
    pedido = f"device/{serial}/request"

    def ao_conectar(cliente, _dados, _flags, razao, _props=None):
        if razao.is_failure:
            recusado["motivo"] = str(razao).replace(codigo, "***")
            pronto.set()
            return
        cliente.subscribe(relatorio)
        cliente.publish(pedido, json.dumps(PUSHALL))

    def ao_receber(_cliente, _dados, mensagem):
        try:
            conteudo = json.loads(mensagem.payload)
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(conteudo, dict):
            return
        acumulador.aplicar(conteudo)
        if acumulador.bruto.get("gcode_state") and acumulador.bruto.get("ams"):
            pronto.set()
            fase = acumulador.bruto["gcode_state"]
            if acompanhar and fase != fase_vista.get("fase"):
                fase_vista["fase"] = fase
                acompanhar(acumulador.estado())

    cliente = fabrica()
    cliente.username_pw_set(USUARIO, codigo)
    # A1 usa CA própria da Bambu: não há o que verificar, e o tráfego é da LAN.
    cliente.tls_set(cert_reqs=ssl.CERT_NONE)
    cliente.tls_insecure_set(True)
    cliente.on_connect = ao_conectar
    cliente.on_message = ao_receber
    try:
        cliente.connect(host, PORTA, keepalive=30)
    except OSError as erro:
        raise ErroStatus(f"Não foi possível alcançar a impressora em {host}.") from erro
    cliente.loop_start()
    try:
        if not pronto.wait(timeout):
            raise ErroStatus("A impressora não respondeu a tempo. Confira IP, serial e código.")
        if recusado:
            raise ErroStatus(f"A impressora recusou a conexão: {recusado['motivo']}")
        if acompanhar:
            threading.Event().wait()  # até Ctrl+C
        return acumulador.estado()
    finally:
        cliente.loop_stop()
        cliente.disconnect()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--acompanhar", action="store_true")
    parser.add_argument("--conferir", metavar="FATIADO")
    args = parser.parse_args(argv)

    try:
        host, serial, codigo = credenciais(cfg.carregar(), cfg.access_code())
        slots = slots_do_fatiado(args.conferir) if args.conferir else None
        acompanhar = cfg.imprimir_json if args.acompanhar else None
        estado = ler(host, serial, codigo, acompanhar=acompanhar)
    except KeyboardInterrupt:
        return 0
    except (ErroStatus, ValueError, OSError) as erro:
        cfg.imprimir_json({"erro": str(erro)})
        return 2
    if slots is not None:
        estado["avisos"] = conferir_ams(estado["bandejas"], slots)
    cfg.imprimir_json(estado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
