# Despertador inteligente da NOVA.
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading
import time

import requests

from core.caminhos import pasta_dados_app
from core.memoria import carregar_memoria_usuario
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_DESPERTADOR = pasta_dados_app() / "despertador_config.json"
TIMEOUT_PADRAO = 4
_thread_monitor = None
_lock_monitor = threading.Lock()


def _limpar_nome_saudacao(nome):
    valor = (nome or "").strip()
    valor = valor.replace("_", " ")
    valor = valor.replace("sr.", "").replace("sra.", "")
    for prefixo in ("senhor ", "senhora "):
        if valor.lower().startswith(prefixo):
            valor = valor[len(prefixo) :]
            break
    return valor.strip() or "Gabriel"


def _config_padrao():
    return {
        "ativo": False,
        "hora": "07:00",
        "cidade": "Sao Paulo",
        "saudacao_nome": "Gabriel",
        "ultimo_disparo": "",
        "mercado_tradicional": ["^BVSP", "^GSPC", "^IXIC"],
        "mercado_cripto": ["bitcoin", "ethereum"],
    }


def carregar_config_despertador(arquivo=ARQUIVO_DESPERTADOR):
    caminho = Path(arquivo)
    dados = carregar_json_seguro(caminho, _config_padrao())
    if not isinstance(dados, dict):
        dados = _config_padrao()

    cfg = _config_padrao()
    cfg.update(dados)
    if not isinstance(cfg.get("mercado_tradicional"), list):
        cfg["mercado_tradicional"] = _config_padrao()["mercado_tradicional"]
    if not isinstance(cfg.get("mercado_cripto"), list):
        cfg["mercado_cripto"] = _config_padrao()["mercado_cripto"]
    return cfg


def salvar_config_despertador(config, arquivo=ARQUIVO_DESPERTADOR):
    cfg = _config_padrao()
    cfg.update(config or {})
    return salvar_json_seguro(Path(arquivo), cfg)


def _validar_hora(hora):
    try:
        datetime.strptime(hora, "%H:%M")
        return True
    except ValueError:
        return False


def configurar_despertador(hora, cidade=None, saudacao_nome=None, ativo=None):
    hora = (hora or "").strip()
    if not _validar_hora(hora):
        return False, "Hora inválida. Use formato HH:MM."

    cfg = carregar_config_despertador()
    cfg["hora"] = hora
    if cidade:
        cfg["cidade"] = cidade.strip().replace("_", " ")
    if saudacao_nome:
        cfg["saudacao_nome"] = _limpar_nome_saudacao(saudacao_nome)
    if ativo is not None:
        cfg["ativo"] = bool(ativo)

    salvar_config_despertador(cfg)
    return True, "Despertador atualizado."


def ativar_despertador():
    cfg = carregar_config_despertador()
    cfg["ativo"] = True
    salvar_config_despertador(cfg)
    return "Despertador ativado."


def desativar_despertador():
    cfg = carregar_config_despertador()
    cfg["ativo"] = False
    salvar_config_despertador(cfg)
    return "Despertador desativado."


def status_despertador():
    cfg = carregar_config_despertador()
    estado = "ativo" if cfg.get("ativo") else "desativado"
    return (
        f"Despertador: {estado}\n"
        f"Horário: {cfg.get('hora')}\n"
        f"Cidade: {cfg.get('cidade')}\n"
        f"Saudação: Senhor {_limpar_nome_saudacao(cfg.get('saudacao_nome'))}\n"
        f"Último disparo: {cfg.get('ultimo_disparo') or 'nenhum'}"
    )


def _clima_resumo(cidade):
    try:
        url = f"https://wttr.in/{cidade}?format=j1"
        resposta = requests.get(url, timeout=TIMEOUT_PADRAO)
        resposta.raise_for_status()
        dados = resposta.json()
        atual = dados.get("current_condition", [{}])[0]
        temp = atual.get("temp_C")
        sensacao = atual.get("FeelsLikeC")
        descricao = (atual.get("weatherDesc", [{}])[0].get("value") or "").lower()
        if temp is None:
            return "não consegui obter o clima agora"
        return f"{descricao}, temperatura de {temp}°C e sensação de {sensacao}°C"
    except Exception:
        return "não consegui obter o clima agora"


def _variacao_seta(valor):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "estável"
    if v > 0:
        return f"em alta ({v:.2f}%)"
    if v < 0:
        return f"em baixa ({v:.2f}%)"
    return "estável (0.00%)"


def _mercado_tradicional_resumo(simbolos):
    try:
        consulta = ",".join(simbolos)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={consulta}"
        resposta = requests.get(url, timeout=TIMEOUT_PADRAO)
        resposta.raise_for_status()
        resultados = resposta.json().get("quoteResponse", {}).get("result", [])
        if not resultados:
            return "sem dados de mercado tradicional no momento"

        partes = []
        for item in resultados[:3]:
            nome = item.get("shortName") or item.get("symbol") or "Índice"
            preco = item.get("regularMarketPrice")
            variacao = _variacao_seta(item.get("regularMarketChangePercent"))
            if preco is None:
                partes.append(f"{nome} {variacao}")
            else:
                partes.append(f"{nome} em {preco} pontos, {variacao}")
        return "; ".join(partes)
    except Exception:
        return "sem dados de mercado tradicional no momento"


def _mercado_cripto_resumo(ids_cripto):
    try:
        ids = ",".join(ids_cripto)
        url = (
            "https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        )
        resposta = requests.get(url, timeout=TIMEOUT_PADRAO)
        resposta.raise_for_status()
        dados = resposta.json()
        if not isinstance(dados, dict) or not dados:
            return "sem dados de cripto no momento"

        mapa_nomes = {"bitcoin": "Bitcoin", "ethereum": "Ethereum"}
        partes = []
        for item_id in ids_cripto[:3]:
            info = dados.get(item_id, {})
            usd = info.get("usd")
            ch = info.get("usd_24h_change")
            nome = mapa_nomes.get(item_id, item_id.title())
            if usd is None:
                partes.append(f"{nome} sem cotação")
            else:
                partes.append(f"{nome} em ${usd:,.2f}, {_variacao_seta(ch)}")
        return "; ".join(partes)
    except Exception:
        return "sem dados de cripto no momento"


def construir_mensagem_despertador():
    cfg = carregar_config_despertador()
    memoria = carregar_memoria_usuario()
    nome = _limpar_nome_saudacao(
        memoria.get("nome_usuario") or cfg.get("saudacao_nome") or "Gabriel"
    )
    cidade = cfg.get("cidade", "Sao Paulo")

    agora = datetime.now()
    semana = [
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    ]
    dia_semana = semana[agora.weekday()]

    clima = _clima_resumo(cidade)
    tradicional = _mercado_tradicional_resumo(cfg.get("mercado_tradicional", []))
    cripto = _mercado_cripto_resumo(cfg.get("mercado_cripto", []))

    return (
        f"Bom dia Senhor {nome}. Hoje é {dia_semana}, {agora.strftime('%d/%m/%Y')}. "
        f"Em {cidade}, o dia está {clima}. "
        f"No mercado financeiro tradicional: {tradicional}. "
        f"No mercado cripto: {cripto}."
    )


def disparar_despertador(falar_callback=None, imprimir_callback=None, forcar=False):
    cfg = carregar_config_despertador()
    if not cfg.get("ativo") and not forcar:
        return False, "Despertador desativado."

    mensagem = construir_mensagem_despertador()
    if callable(imprimir_callback):
        imprimir_callback(mensagem)
    if callable(falar_callback):
        try:
            falar_callback(mensagem)
        except Exception:
            pass

    cfg["ultimo_disparo"] = datetime.now().isoformat(timespec="seconds")
    salvar_config_despertador(cfg)
    return True, mensagem


def _deve_disparar_agora(cfg):
    if not cfg.get("ativo"):
        return False
    agora = datetime.now()
    alvo = str(cfg.get("hora", "07:00"))
    atual = agora.strftime("%H:%M")
    if atual != alvo:
        return False

    ultimo = str(cfg.get("ultimo_disparo", ""))
    hoje = agora.strftime("%Y-%m-%d")
    return not ultimo.startswith(hoje)


def iniciar_monitor_despertador(falar_callback=None, imprimir_callback=None):
    global _thread_monitor
    with _lock_monitor:
        if _thread_monitor and _thread_monitor.is_alive():
            return

        def loop():
            while True:
                try:
                    cfg = carregar_config_despertador()
                    if _deve_disparar_agora(cfg):
                        disparar_despertador(
                            falar_callback=falar_callback,
                            imprimir_callback=imprimir_callback,
                            forcar=True,
                        )
                except Exception:
                    pass
                time.sleep(20)

        _thread_monitor = threading.Thread(target=loop, name="nova-despertador", daemon=True)
        _thread_monitor.start()
