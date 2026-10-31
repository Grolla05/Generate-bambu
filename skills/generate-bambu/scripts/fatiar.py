"""Fatia um .3mf da skill pelo CLI do Bambu Studio, sem interface e sem clique.

    python fatiar.py <peca>.3mf [--abrir]

Grava em <pasta da peça>/_fatiados/<peca>/<peca>.gcode.3mf e devolve JSON com tempo,
gramas, camadas e dimensões. --abrir mostra o resultado no Bambu Studio.

ESTE SCRIPT NÃO IMPRIME. Não fala com a impressora: quem manda imprimir é o usuário, no
botão Print plate.

Códigos de saída: 0 ok, 2 entrada inválida, 3 Bambu Studio recusou, 4 Bambu Studio ausente.

Validado no Bambu Studio 02.08.03.66. O CLI grava `result.json` (`return_code`,
`error_string`) no diretório de saída.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "helpers"))

import bambu_3mf  # noqa: E402
import config as cfg  # noqa: E402
import diagnostico  # noqa: E402
import perfis  # noqa: E402
import projeto_bambu  # noqa: E402
from agrupar_3mf import ler_slots_fusion  # noqa: E402

ARQUIVO_FATIADO = "fatiado.3mf"
PASTA_FATIADOS = "_fatiados"
# A torre cresce com cores e altura: se sair da mesa ou bater na peça, desce e tenta de novo.
# Valores da mesa de 256 mm, proporcionais nas outras.
Y_TORRE = (207.957, 160.0, 110.0)
MESA_DE_REFERENCIA_MM = 256
ERROS_DE_TORRE = {-101, -104}
TOLERANCIA_MM = 0.5
_SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_DESTACADO = getattr(subprocess, "DETACHED_PROCESS", 0)


class ErroFatiamento(ValueError):
    """O CLI não conseguiu fatiar ou o resultado não bate com a peça."""

    def __init__(self, mensagem, codigo=None):
        super().__init__(mensagem)
        self.codigo = codigo


def _ler_resultado(pasta, codigo_saida):
    try:
        resultado = json.loads((pasta / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        raise ErroFatiamento(
            f"O Bambu Studio não gerou result.json (código de saída {codigo_saida})."
        ) from erro
    if not isinstance(resultado, dict):
        raise ErroFatiamento("O result.json do Bambu Studio veio em formato inesperado.")
    return resultado


def fatiar(exe, projeto, pasta, *, timeout_s=600, executar=subprocess.run):
    """Fatia a placa 1 de `projeto` em `pasta`. Devolve (arquivo fatiado, result.json)."""
    comando = [str(exe), "--arrange", "0", "--slice", "1", "--outputdir", str(pasta),
               "--export-3mf", ARQUIVO_FATIADO, str(projeto)]
    try:
        processo = executar(comando, cwd=pasta, capture_output=True, timeout=timeout_s,
                            check=False, creationflags=_SEM_JANELA)
    except subprocess.TimeoutExpired as erro:
        raise ErroFatiamento(f"O fatiamento passou do tempo limite ({timeout_s:.0f} s).") from erro
    except OSError as erro:
        raise ErroFatiamento(f"Não foi possível executar o Bambu Studio em {exe}: {erro}") from erro

    resultado = _ler_resultado(pasta, processo.returncode)
    codigo = resultado.get("return_code")
    if codigo != 0:
        raise ErroFatiamento(
            f"O Bambu Studio recusou o fatiamento (código {codigo}): "
            f"{resultado.get('error_string', 'sem mensagem')}",
            codigo,
        )
    arquivo = pasta / ARQUIVO_FATIADO
    if not arquivo.is_file():
        raise ErroFatiamento("O Bambu Studio terminou, mas não gravou o 3mf fatiado.")
    return arquivo, resultado


def _dimensoes(resultado):
    """[largura, profundidade, altura] que o próprio slicer mediu, se ele informou."""
    try:
        caixa = resultado["sliced_plates"][0]["objects"][0]["bbox"]
        return [round(caixa[k], 2) for k in ("width", "depth", "height")]
    except (KeyError, IndexError, TypeError):
        return None


def conferir(resumo, medidas, esperado, camada, slots):
    """Divergência aqui é erro: arquivo errado não pode seguir para a pergunta do passo 6."""
    if not resumo.fatiado:
        raise ErroFatiamento("O Bambu Studio terminou, mas o 3mf não ficou fatiado.")
    if resumo.camada_mm is None or abs(resumo.camada_mm - camada) > 1e-6:
        raise ErroFatiamento(f"Camada {resumo.camada_mm} mm no fatiado; o perfil pede {camada} mm.")
    usados = [f for f in resumo.filamentos if f.usado_g > 0]
    if len(usados) != len(slots):
        raise ErroFatiamento(f"{len(usados)} filamentos usados para {len(slots)} slots.")
    if medidas and any(abs(m - e) > TOLERANCIA_MM for m, e in zip(medidas, esperado, strict=True)):
        raise ErroFatiamento(f"Dimensões {medidas} no fatiado; a peça mede {esperado}.")


def _rgb(cor):
    return bambu_3mf.normalizar_hex(cor) if cor else "#CCCCCC"


def processar(entrada, config, bambu, *, executar=subprocess.run):
    """Do .3mf da skill ao fatiado conferido. Devolve o relatório."""
    entrada = Path(entrada)
    maquina = config["maquina"]
    mesa = maquina["mesa_mm"]
    slots, avisos = ler_slots_fusion(entrada, agrupado=True, max_slots=maquina["slots"])
    cores = [_rgb(s["cor"]) for s in slots]
    xmin, ymin, zmin, xmax, ymax, zmax = projeto_bambu.caixa(slots)
    largura, profundidade = xmax - xmin, ymax - ymin
    esperado = [round(v, 2) for v in (largura, profundidade, zmax - zmin)]
    if any(v > maquina["limite_mm"] for v in esperado):
        raise projeto_bambu.ErroPeca(
            f"Peça de {esperado} mm não cabe: o limite da {maquina['modelo']} é "
            f"{maquina['limite_mm']} mm."
        )

    secao = config["bambu_studio"]
    versao = bambu.get("versao") or perfis.VERSAO_TESTADA
    if versao != perfis.VERSAO_TESTADA:
        avisos.append(f"Bambu Studio {versao}: testado na {perfis.VERSAO_TESTADA}.")
    perfis_bbl = perfis.pasta_perfis(bambu["exe"])

    destino = entrada.parent / PASTA_FATIADOS / entrada.stem
    destino.mkdir(parents=True, exist_ok=True)
    ultimo_erro = None
    with tempfile.TemporaryDirectory(dir=destino) as temporario:
        pasta = Path(temporario)
        for y_base in Y_TORRE:
            y_torre = round(y_base * mesa / MESA_DE_REFERENCIA_MM, 3)
            posicao = projeto_bambu.posicionar(largura, profundidade, len(slots), y_torre, mesa)
            if posicao is None:
                continue
            configuracao = perfis.config_projeto(perfis_bbl, secao, cores, versao, y_torre)
            projeto = pasta / "projeto.3mf"
            projeto_bambu.gravar_projeto(
                slots, projeto, configuracao, entrada.stem, versao, posicao
            )
            try:
                arquivo, resultado = fatiar(bambu["exe"], projeto, pasta, executar=executar)
            except ErroFatiamento as erro:
                ultimo_erro = erro
                if erro.codigo in ERROS_DE_TORRE and len(slots) > 1:
                    continue
                raise
            resumo = bambu_3mf.ler_3mf(arquivo)
            medidas = _dimensoes(resultado)
            conferir(resumo, medidas, esperado, float(configuracao["layer_height"]), slots)
            final = destino / f"{entrada.stem}.gcode.3mf"
            shutil.move(str(arquivo), str(final))
            return {
                "arquivo": str(final),
                "tempo_s": resumo.tempo_estimado_s,
                "peso_g": resumo.peso_g,
                "camadas": resumo.camadas_total,
                "camada_mm": resumo.camada_mm,
                "dimensoes_mm": medidas or esperado,
                "filamentos": [
                    {"slot": s["slot"], "cor": f.cor_hex, "g": f.usado_g}
                    for s, f in zip(slots, resumo.filamentos, strict=True)
                ],
                "avisos": avisos + list(resumo.avisos),
            }
    if ultimo_erro:
        raise ErroFatiamento(
            f"Sem lugar para a torre de purga nesta mesa. {ultimo_erro}", ultimo_erro.codigo
        )
    raise projeto_bambu.ErroPeca(
        f"Peça multicor de {largura:.0f} × {profundidade:.0f} mm não deixa lugar para a torre de "
        f"purga: reduza um dos lados para até {projeto_bambu.maior_lado_multicor(mesa):.0f} mm."
    )


def abrir_no_bambu(exe, arquivo):
    """Só mostra o arquivo. Imprimir continua sendo clique do usuário."""
    subprocess.Popen([str(exe), str(arquivo)], creationflags=_DESTACADO, close_fds=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("entrada", help=".3mf gerado no passo 3")
    parser.add_argument("--abrir", action="store_true", help="mostra o fatiado no Bambu Studio")
    args = parser.parse_args(argv)

    config = cfg.carregar()
    bambu = diagnostico.achar_bambu_studio(config)
    if not bambu["exe"]:
        cfg.imprimir_json({"erro": bambu.get("erro") or "Bambu Studio não encontrado."})
        return 4
    try:
        relatorio = processar(args.entrada, config, bambu)
    except ErroFatiamento as erro:
        cfg.imprimir_json({"erro": str(erro), "codigo": erro.codigo})
        return 3
    except (OSError, ValueError, KeyError) as erro:
        cfg.imprimir_json({"erro": str(erro)})
        return 2
    if args.abrir:
        abrir_no_bambu(bambu["exe"], relatorio["arquivo"])
    cfg.imprimir_json(relatorio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
