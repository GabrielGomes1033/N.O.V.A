# Orquestrador JARVIS fase 2:
# execução contínua em background + fila de tarefas + relatórios proativos.
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

from core.agente import executar_objetivo_background, gerar_panorama_mercado
from core.caminhos import pasta_dados_app
from core.memoria import carregar_memoria_usuario
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_JARVIS2 = pasta_dados_app() / "jarvis2_state.json"
_thread_runtime = None
_lock = threading.Lock()
_callback_notificacao = None


def _estado_padrao():
    return {
        "enabled": False,
        "report_interval_min": 30,
        "last_report_at": "",
        "next_task_id": 1,
        "queue": [],
        "history": [],
        "last_report": "",
    }


def _agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def carregar_estado():
    caminho = Path(ARQUIVO_JARVIS2)
    dados = carregar_json_seguro(caminho, _estado_padrao())
    if not isinstance(dados, dict):
        dados = _estado_padrao()
    estado = _estado_padrao()
    estado.update(dados)
    if not isinstance(estado.get("queue"), list):
        estado["queue"] = []
    if not isinstance(estado.get("history"), list):
        estado["history"] = []
    return estado


def salvar_estado(estado):
    return salvar_json_seguro(Path(ARQUIVO_JARVIS2), estado)


def _notificar(msg):
    if callable(_callback_notificacao):
        try:
            _callback_notificacao(msg)
        except Exception:
            pass


def iniciar_runtime(callback_notificacao=None):
    global _thread_runtime, _callback_notificacao
    _callback_notificacao = callback_notificacao or _callback_notificacao
    with _lock:
        if _thread_runtime and _thread_runtime.is_alive():
            return

        def loop():
            while True:
                try:
                    _tick_runtime()
                except Exception:
                    pass
                time.sleep(4)

        _thread_runtime = threading.Thread(target=loop, name="nova-jarvis-fase2", daemon=True)
        _thread_runtime.start()


def _pegar_proxima_tarefa(estado):
    for tarefa in estado.get("queue", []):
        if tarefa.get("status") == "pendente":
            return tarefa
    return None


def _deve_gerar_relatorio(estado):
    if not estado.get("enabled"):
        return False
    ultimo = str(estado.get("last_report_at", "") or "")
    intervalo = int(estado.get("report_interval_min", 30) or 30)
    if intervalo < 1:
        intervalo = 1
    if not ultimo:
        return True
    try:
        ultimo_dt = datetime.fromisoformat(ultimo)
    except ValueError:
        return True
    return datetime.now() >= (ultimo_dt + timedelta(minutes=intervalo))


def _gerar_relatorio(estado):
    memoria = carregar_memoria_usuario()
    nome = memoria.get("nome_usuario") or "usuário"
    objetivos = memoria.get("objetivos_recentes", [])
    ult_obj = objetivos[-1] if isinstance(objetivos, list) and objetivos else "nenhum objetivo recente"
    pendentes = [t for t in estado.get("queue", []) if t.get("status") == "pendente"]
    executando = [t for t in estado.get("queue", []) if t.get("status") == "executando"]
    mercado = gerar_panorama_mercado()
    return (
        f"Relatório proativo JARVIS: Olá, {nome}. "
        f"Pendentes: {len(pendentes)}. Executando: {len(executando)}. "
        f"Último objetivo lembrado: {ult_obj}. {mercado}"
    )


def _tick_runtime():
    estado = carregar_estado()
    if not estado.get("enabled"):
        return

    tarefa = _pegar_proxima_tarefa(estado)
    if tarefa:
        tarefa["status"] = "executando"
        tarefa["iniciado_em"] = _agora_iso()
        salvar_estado(estado)

        resultado = executar_objetivo_background(tarefa.get("objetivo", ""), contexto={})
        tarefa["status"] = "concluido" if resultado.get("ok") else "falhou"
        tarefa["concluido_em"] = _agora_iso()
        tarefa["resultado"] = resultado.get("resumo", "")
        tarefa["meta"] = {
            "passos_total": resultado.get("passos_total", 0),
            "passos_pulados": resultado.get("passos_pulados", 0),
            "passos_falhos": resultado.get("passos_falhos", 0),
        }
        estado["history"] = (estado.get("history", []) + [tarefa.copy()])[-200:]
        salvar_estado(estado)
        _notificar(f"JARVIS: tarefa #{tarefa.get('id')} {tarefa['status']}. {tarefa.get('resultado', '')}")
        return

    if _deve_gerar_relatorio(estado):
        rel = _gerar_relatorio(estado)
        estado["last_report_at"] = _agora_iso()
        estado["last_report"] = rel
        salvar_estado(estado)
        _notificar(rel)


def ligar_fase2(report_interval_min=30):
    estado = carregar_estado()
    try:
        intervalo = int(report_interval_min)
    except (TypeError, ValueError):
        intervalo = 30
    estado["enabled"] = True
    estado["report_interval_min"] = max(1, intervalo)
    salvar_estado(estado)
    return "JARVIS fase 2 ativado."


def desligar_fase2():
    estado = carregar_estado()
    estado["enabled"] = False
    salvar_estado(estado)
    return "JARVIS fase 2 desativado."


def enfileirar_tarefa(objetivo, origem="manual"):
    objetivo = (objetivo or "").strip()
    if not objetivo:
        return False, "Objetivo vazio."
    estado = carregar_estado()
    task_id = int(estado.get("next_task_id", 1))
    tarefa = {
        "id": task_id,
        "objetivo": objetivo,
        "origem": origem,
        "status": "pendente",
        "criado_em": _agora_iso(),
        "iniciado_em": "",
        "concluido_em": "",
        "resultado": "",
        "meta": {},
    }
    estado["queue"].append(tarefa)
    estado["next_task_id"] = task_id + 1
    salvar_estado(estado)
    return True, f"Tarefa #{task_id} adicionada à fila."


def limpar_fila():
    estado = carregar_estado()
    removidas = len(estado.get("queue", []))
    estado["queue"] = []
    salvar_estado(estado)
    return f"Fila limpa. {removidas} tarefa(s) removida(s)."


def listar_fila(limit=12):
    estado = carregar_estado()
    itens = estado.get("queue", [])
    if not itens:
        return "Fila vazia."
    linhas = []
    for item in itens[:limit]:
        linhas.append(f"#{item.get('id')} [{item.get('status')}] {item.get('objetivo')}")
    return "Fila JARVIS:\n" + "\n".join(linhas)


def status_fase2():
    estado = carregar_estado()
    pendentes = len([t for t in estado.get("queue", []) if t.get("status") == "pendente"])
    executando = len([t for t in estado.get("queue", []) if t.get("status") == "executando"])
    concluidas = len([t for t in estado.get("history", []) if t.get("status") == "concluido"])
    falhas = len([t for t in estado.get("history", []) if t.get("status") == "falhou"])
    ligado = "ativo" if estado.get("enabled") else "desativado"
    return (
        f"JARVIS fase 2: {ligado}\n"
        f"Intervalo de relatório: {estado.get('report_interval_min', 30)} min\n"
        f"Fila pendente: {pendentes}\n"
        f"Fila executando: {executando}\n"
        f"Histórico concluídas: {concluidas}\n"
        f"Histórico falhas: {falhas}\n"
        f"Último relatório: {estado.get('last_report_at') or 'nenhum'}"
    )


def relatorio_agora():
    estado = carregar_estado()
    rel = _gerar_relatorio(estado)
    estado["last_report_at"] = _agora_iso()
    estado["last_report"] = rel
    salvar_estado(estado)
    return rel
