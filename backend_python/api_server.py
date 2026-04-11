from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.admin import autenticar_admin, configurar_admin, explicacao_completa_admin, status_admin
from core.agente import eh_pedido_de_agente, executar_agente, processar_confirmacao_agente
from core.despertador import (
    configurar_despertador,
    desativar_despertador,
    disparar_despertador,
    iniciar_monitor_despertador,
    status_despertador,
)
from core.jarvis_fase2 import (
    enfileirar_tarefa,
    iniciar_runtime as iniciar_runtime_fase2,
    ligar_fase2,
    desligar_fase2,
    limpar_fila,
    listar_fila,
    relatorio_agora,
    status_fase2,
)
from core.backup_drive import restaurar_backup_drive, sincronizar_backup_drive, status_backup_drive
from core.memoria import carregar_memoria_usuario, formatar_memoria_usuario, salvar_memoria_usuario, registrar_interacao_usuario
from core.pesquisa import gerar_pesquisa_wikipedia
from core.respostas import carregar_aprendizado, detectar_intencao, extrair_nome_usuario, responder, salvar_aprendizado
from core.voz import falar


def _novo_contexto():
    memoria = carregar_memoria_usuario()
    return {
        "nome_usuario": memoria.get("nome_usuario", ""),
        "idioma_preferido": memoria.get("idioma_preferido", "pt"),
        "tratamento": memoria.get("tratamento", ""),
        "ultima_intencao": "",
        "confirmacao_pendente": None,
        "admin_autenticado": False,
        "admin_usuario": "",
    }


CONTEXTO = _novo_contexto()


def sincronizar_memoria():
    memoria = carregar_memoria_usuario()
    memoria["nome_usuario"] = CONTEXTO.get("nome_usuario", "")
    memoria["idioma_preferido"] = CONTEXTO.get("idioma_preferido", "pt")
    memoria["tratamento"] = CONTEXTO.get("tratamento", "")
    salvar_memoria_usuario(memoria)


def _cmd_admin(texto):
    partes = texto.strip().split()
    if len(partes) == 1:
        return (
            "Comandos admin: /admin login <usuario> <senha> | /admin logout | /admin status | "
            "/admin explicar | /admin configurar <usuario> <senha> | "
            "/admin despertador status|ligar|desligar|testar"
        )

    acao = partes[1].lower()
    if acao == "login":
        if len(partes) < 4:
            return "Use /admin login <usuario> <senha>."
        if autenticar_admin(partes[2], partes[3]):
            CONTEXTO["admin_autenticado"] = True
            CONTEXTO["admin_usuario"] = partes[2]
            return f"Login admin confirmado para {partes[2]}."
        return "Credenciais de admin inválidas."

    if acao == "logout":
        CONTEXTO["admin_autenticado"] = False
        CONTEXTO["admin_usuario"] = ""
        return "Sessão admin encerrada."

    if acao in {"status", "explicar", "configurar", "despertador", "jarvis2", "drivebackup"} and not CONTEXTO.get("admin_autenticado"):
        return "Comando restrito. Faça /admin login primeiro."

    if acao == "status":
        return status_admin()
    if acao == "explicar":
        return explicacao_completa_admin()
    if acao == "configurar":
        if len(partes) < 4:
            return "Use /admin configurar <usuario> <senha>."
        ok, msg = configurar_admin(partes[2], partes[3])
        if ok:
            CONTEXTO["admin_usuario"] = partes[2]
        return msg

    if acao == "despertador":
        if len(partes) < 3:
            return "Use /admin despertador status|ligar HH:MM [cidade] [nome]|desligar|testar"
        sub = partes[2].lower()
        if sub == "status":
            return status_despertador()
        if sub == "desligar":
            return desativar_despertador()
        if sub == "testar":
            _, msg = disparar_despertador(falar_callback=falar, forcar=True)
            return msg
        if sub == "ligar":
            if len(partes) < 4:
                return "Use /admin despertador ligar HH:MM [cidade] [nome]."
            hora = partes[3]
            cidade = partes[4] if len(partes) >= 5 else None
            nome = " ".join(partes[5:]) if len(partes) >= 6 else None
            ok, msg = configurar_despertador(hora=hora, cidade=cidade, saudacao_nome=nome, ativo=True)
            if ok:
                iniciar_monitor_despertador(falar_callback=falar)
            return msg
        return "Subcomando de despertador não reconhecido."

    if acao == "jarvis2":
        if len(partes) < 3:
            return (
                "Use /admin jarvis2 status|ligar [intervalo]|desligar|enfileirar <objetivo>|"
                "fila|limpar|relatorio"
            )
        sub = partes[2].lower()
        if sub == "status":
            return status_fase2()
        if sub == "ligar":
            intervalo = 30
            if len(partes) >= 4:
                try:
                    intervalo = int(partes[3])
                except ValueError:
                    intervalo = 30
            iniciar_runtime_fase2()
            return ligar_fase2(intervalo)
        if sub == "desligar":
            return desligar_fase2()
        if sub == "enfileirar":
            objetivo = " ".join(partes[3:]).strip()
            ok, msg = enfileirar_tarefa(objetivo, origem="admin_api")
            return msg
        if sub == "fila":
            return listar_fila()
        if sub == "limpar":
            return limpar_fila()
        if sub == "relatorio":
            return relatorio_agora()
        return "Subcomando jarvis2 não reconhecido."

    if acao == "drivebackup":
        if len(partes) < 3:
            return "Use /admin drivebackup status|sincronizar|restaurar"
        sub = partes[2].lower()
        if sub == "status":
            return status_backup_drive()
        if sub == "sincronizar":
            ok, msg = sincronizar_backup_drive()
            return msg
        if sub == "restaurar":
            ok, msg = restaurar_backup_drive()
            return msg
        return "Subcomando drivebackup não reconhecido."

    return "Comando admin não reconhecido."


def processar_mensagem(user):
    user = (user or "").strip()
    def ret(msg):
        registrar_interacao_usuario(user, msg)
        return msg

    if not user:
        return ret("Mensagem vazia.")

    if CONTEXTO.get("confirmacao_pendente"):
        resp_confirm = processar_confirmacao_agente(user, contexto=CONTEXTO)
        if resp_confirm:
            return ret(resp_confirm)

    if user.startswith("/ensinar"):
        try:
            _, conteudo = user.split(" ", 1)
            pergunta, resposta_txt = conteudo.split("=", 1)
            total = salvar_aprendizado(pergunta.strip(), resposta_txt.strip())
            return ret(f"Aprendi! ({total} respostas salvas).")
        except Exception:
            return ret("Use /ensinar pergunta = resposta.")

    if user.startswith("/google"):
        try:
            _, consulta = user.split(" ", 1)
            wiki = gerar_pesquisa_wikipedia(consulta)
            if wiki:
                return ret(f"{wiki['titulo']}\n{wiki['resumo']}")
            return ret("Não achei resumo disponível para esse tema no momento.")
        except Exception:
            return ret("Use /google algo.")

    if user.startswith("/nome"):
        try:
            _, nome = user.split(" ", 1)
            CONTEXTO["nome_usuario"] = nome.strip().title()
            sincronizar_memoria()
            return ret(f"Beleza, vou te chamar de {CONTEXTO['nome_usuario']}.")
        except Exception:
            return ret("Use /nome SeuNome.")

    if user.startswith("/memoria"):
        return ret(formatar_memoria_usuario(carregar_memoria_usuario()))

    if user.startswith("/admin"):
        return ret(_cmd_admin(user))

    if user.startswith("/nova") or user.startswith("/agente") or eh_pedido_de_agente(user):
        resultado = executar_agente(user, contexto=CONTEXTO)
        CONTEXTO["confirmacao_pendente"] = resultado.get("confirmacao_pendente")
        sincronizar_memoria()
        return ret(resultado.get("mensagem", "Plano executado."))

    nome = extrair_nome_usuario(user)
    if nome:
        CONTEXTO["nome_usuario"] = nome
        sincronizar_memoria()

    intencao = detectar_intencao(user, CONTEXTO)
    CONTEXTO["ultima_intencao"] = intencao
    resposta = responder(user, contexto=CONTEXTO)
    try:
        falar(resposta)
    except Exception:
        pass
    return ret(resposta)


class NovaHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=HTTPStatus.OK):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"ok": True, "service": "nova-api"})
            return
        if self.path == "/backup/export":
            self._send_json(
                {
                    "ok": True,
                    "backup": {
                        "memory": carregar_memoria_usuario(),
                    },
                }
            )
            return
        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
            return

        if self.path == "/chat":
            message = str(body.get("message", "")).strip()
            reply = processar_mensagem(message)
            self._send_json({"ok": True, "reply": reply})
            return

        if self.path == "/backup/restore":
            backup = body.get("backup", {})
            memory = backup.get("memory", {}) if isinstance(backup, dict) else {}
            if not isinstance(memory, dict):
                self._send_json({"ok": False, "error": "invalid_backup"}, status=HTTPStatus.BAD_REQUEST)
                return
            salvar_memoria_usuario(memory)
            self._send_json({"ok": True, "restored": True})
            return

        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Servidor HTTP da NOVA")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    args = parser.parse_args()

    try:
        carregar_memoria_usuario()
        carregar_aprendizado()
        iniciar_monitor_despertador(falar_callback=falar)
        iniciar_runtime_fase2()
    except Exception:
        pass

    server = ThreadingHTTPServer((args.host, args.port), NovaHandler)
    print(f"NOVA API online em http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
