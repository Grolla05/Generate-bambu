"""Testa a leitura da impressora com um cliente falso, sem rede e sem A1."""

import json
import os
import sys
from pathlib import Path

import config as cfg
import pytest
import status as st

# Capturas reais da A1 ficam fora do repositório público: trazem serial e rede.
RAIZ_FIXTURES = Path(os.environ.get("BAMBU_FIXTURES", "nao-definido"))
PUSHALL = {
    "print": {
        "gcode_state": "IDLE",
        "mc_percent": 0,
        "layer_num": 0,
        "nozzle_temper": 24.5,
        "bed_temper": 23,
        "print_error": 0,
        "ams": {
            "tray_now": "255",
            "tray_exist_bits": "7",
            "ams": [{"id": "0", "tray": [
                {"id": "0", "tray_type": "PLA", "tray_color": "E8B647FF"},
                {"id": "1", "tray_type": "PETG", "tray_color": "1A73E8FF"},
                {"id": "2", "tray_type": "PLA", "tray_color": "000000FF"},
                {"id": "3", "tray_type": "", "tray_color": "00000000"},
            ]}],
        },
    }
}


class ClienteFalso:
    """Imita o paho: conecta na hora e responde o pushall."""

    def __init__(self, recusar=False):
        self.recusar = recusar
        self.publicados = []
        self.assinados = []
        self.on_connect = self.on_message = None

    def username_pw_set(self, usuario, codigo):
        self.credencial = (usuario, codigo)

    def tls_set(self, **_):
        pass

    def tls_insecure_set(self, _):
        pass

    def connect(self, host, porta, keepalive):
        self.destino = (host, porta)

    def loop_start(self):
        razao = type("R", (), {"is_failure": self.recusar, "__str__": lambda s: "negado abc123"})()
        self.on_connect(self, None, None, razao)

    def loop_stop(self):
        pass

    def disconnect(self):
        pass

    def subscribe(self, topico):
        self.assinados.append(topico)

    def publish(self, topico, carga):
        self.publicados.append((topico, json.loads(carga)))
        mensagem = type("M", (), {"payload": json.dumps(PUSHALL).encode()})()
        self.on_message(self, None, mensagem)


def test_le_estado_e_ams():
    cliente = ClienteFalso()

    r = st.ler("192.0.2.1", "SERIAL", "abc123", fabrica=lambda: cliente)

    assert r["fase"] == "IDLE" and r["ativa"] is False
    assert r["bandejas"][0] == {"slot": 1, "material": "PLA", "cor": "#E8B647",
                                "em_uso": False, "vazia": False}
    assert r["bandejas"][3]["vazia"] is True
    assert cliente.destino == ("192.0.2.1", 8883)
    assert cliente.credencial == ("bblp", "abc123")


def test_unico_comando_publicado_e_pushall():
    cliente = ClienteFalso()

    st.ler("192.0.2.1", "SERIAL", "abc123", fabrica=lambda: cliente)

    assert cliente.publicados == [("device/SERIAL/request", st.PUSHALL)]
    assert cliente.assinados == ["device/SERIAL/report"]


def test_script_nao_tem_comando_que_mexa_na_impressao():
    fonte = Path(st.__file__).read_text(encoding="utf-8")
    codigo = fonte.split('"""', 2)[2]

    for proibido in ("project_file", '"pause"', '"resume"', '"stop"', "ftplib", "gcode_line"):
        assert proibido not in codigo


def test_recusa_nao_vaza_o_codigo():
    with pytest.raises(st.ErroStatus) as erro:
        st.ler("192.0.2.1", "S", "abc123", fabrica=lambda: ClienteFalso(recusar=True))

    assert "abc123" not in str(erro.value)


def test_sem_resposta():
    class Mudo(ClienteFalso):
        def publish(self, topico, carga):
            pass

    with pytest.raises(st.ErroStatus, match="não respondeu"):
        st.ler("192.0.2.1", "S", "x", timeout=0.05, fabrica=Mudo)


def test_rede_fora():
    class SemRede(ClienteFalso):
        def connect(self, host, porta, keepalive):
            raise OSError("sem rota")

    with pytest.raises(st.ErroStatus, match="alcançar"):
        st.ler("192.0.2.1", "S", "x", fabrica=SemRede)


def test_paho_ausente(monkeypatch):
    monkeypatch.setitem(sys.modules, "paho.mqtt.client", None)
    monkeypatch.setitem(sys.modules, "paho", None)

    with pytest.raises(st.ErroStatus, match="pip install"):
        st._paho()


def test_delta_nao_apaga_as_bandejas():
    a = st.Acumulador()
    a.aplicar(PUSHALL)

    a.aplicar({"print": {"mc_percent": 40, "ams": {"tray_now": "1"}}})

    r = a.estado()
    assert r["percentual"] == 40
    assert len(r["bandejas"]) == 4
    assert r["bandejas"][1]["em_uso"] is True


def test_mensagem_sem_print_e_ignorada():
    a = st.Acumulador()

    a.aplicar({"info": {"command": "get_version"}})

    assert a.bruto == {}


def test_conferir_aponta_o_que_nao_bate():
    bandejas = st.Acumulador()
    bandejas.aplicar(PUSHALL)
    b = bandejas.estado()["bandejas"]
    slots = [
        {"slot": 1, "material": "PLA", "cor": "#E8B647"},
        {"slot": 2, "material": "PLA", "cor": "#1A73E8"},
        {"slot": 3, "material": "PLA", "cor": "#FFFFFF"},
        {"slot": 4, "material": "PLA", "cor": "#123456"},
    ]

    avisos = st.conferir_ams(b, slots)

    assert not any(a.startswith("slot1") for a in avisos)
    assert any(a.startswith("slot2") and "PETG" in a for a in avisos)
    assert any(a.startswith("slot3") and "cor" in a for a in avisos)
    assert any(a.startswith("slot4") and "vazia" in a for a in avisos)


def test_credenciais_dizem_o_que_falta():
    config = json.loads(json.dumps(cfg.PADRAO))

    with pytest.raises(st.ErroStatus, match="impressora.host.*access code"):
        st.credenciais(config, None)


@pytest.mark.skipif(not RAIZ_FIXTURES.is_dir(), reason="defina BAMBU_FIXTURES para rodar")
def test_formato_real_da_a1():
    a = st.Acumulador()
    a.aplicar(json.loads((RAIZ_FIXTURES / "bambu_pushall_ocioso.json").read_text("utf-8")))
    for linha in (RAIZ_FIXTURES / "bambu_deltas_imprimindo.jsonl").read_text("utf-8").splitlines():
        if linha.strip():
            a.aplicar(json.loads(linha))

    r = a.estado()

    assert r["fase"]
    assert r["bandejas"]
