from datetime import datetime
import traceback
from pathlib import Path
import sys
from urllib.parse import quote_plus
import webbrowser

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# =========================
# LOG DE ERRO
# =========================
def registrar_erro(exc):
    caminho = Path("erro_log.txt")
    conteudo = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


# =========================
# FALLBACK (caso core falhe)
# =========================
def responder(texto, respostas_txt=None, modo="normal", arquivo_aprendizado=None, contexto=None):
    return "Ainda estou em modo básico."

def carregar_aprendizado(_arquivo=None):
    return {}

def detectar_intencao(texto, contexto=None):
    return "desconhecida"

def extrair_nome_usuario(texto):
    return ""

def salvar_aprendizado(pergunta, resposta):
    return 1

def gerar_pesquisa_wikipedia(_):
    return None

def falar(_):
    return False

def executar_agente(objetivo, contexto=None):
    return {"mensagem": "Modo agente indisponível no momento.", "confirmacao_pendente": None}

def processar_confirmacao_agente(texto, contexto=None):
    return None

def eh_pedido_de_agente(texto):
    return False

def carregar_memoria_usuario():
    return {"nome_usuario": "", "idioma_preferido": "pt", "tratamento": "", "topicos_favoritos": []}

def salvar_memoria_usuario(memoria):
    return memoria

def formatar_memoria_usuario(memoria):
    return f"Memória atual: {memoria}"

def registrar_interacao_usuario(entrada, resposta):
    return None

def autenticar_admin(usuario, senha):
    return False

def configurar_admin(usuario, senha):
    return False, "Admin indisponível."

def status_admin():
    return "Admin indisponível."

def explicacao_completa_admin():
    return "Admin indisponível."

def iniciar_monitor_despertador(falar_callback=None, imprimir_callback=None):
    return None

def status_despertador():
    return "Despertador indisponível."

def configurar_despertador(hora, cidade=None, saudacao_nome=None, ativo=None):
    return False, "Despertador indisponível."

def ativar_despertador():
    return "Despertador indisponível."

def desativar_despertador():
    return "Despertador indisponível."

def disparar_despertador(falar_callback=None, imprimir_callback=None, forcar=False):
    return False, "Despertador indisponível."

def iniciar_runtime_fase2(callback_notificacao=None):
    return None

def ligar_fase2(report_interval_min=30):
    return "JARVIS fase 2 indisponível."

def desligar_fase2():
    return "JARVIS fase 2 indisponível."

def enfileirar_tarefa_fase2(objetivo, origem="manual"):
    return False, "JARVIS fase 2 indisponível."

def listar_fila_fase2(limit=12):
    return "JARVIS fase 2 indisponível."

def limpar_fila_fase2():
    return "JARVIS fase 2 indisponível."

def status_fase2():
    return "JARVIS fase 2 indisponível."

def relatorio_agora_fase2():
    return "JARVIS fase 2 indisponível."

def status_backup_drive():
    return "Backup Drive indisponível."

def sincronizar_backup_drive():
    return False, "Backup Drive indisponível."

def restaurar_backup_drive():
    return False, "Backup Drive indisponível."


# =========================
# IMPORTA CORE (se existir)
# =========================
try:
    from core.respostas import responder, detectar_intencao, extrair_nome_usuario, salvar_aprendizado, carregar_aprendizado
    from core.pesquisa import gerar_pesquisa_wikipedia
    from core.voz import falar
    from core.agente import executar_agente, processar_confirmacao_agente, eh_pedido_de_agente
    from core.memoria import carregar_memoria_usuario, salvar_memoria_usuario, formatar_memoria_usuario, registrar_interacao_usuario
    from core.admin import autenticar_admin, configurar_admin, status_admin, explicacao_completa_admin
    from core.despertador import (
        iniciar_monitor_despertador,
        status_despertador,
        configurar_despertador,
        ativar_despertador,
        desativar_despertador,
        disparar_despertador,
    )
    from core.jarvis_fase2 import (
        iniciar_runtime as iniciar_runtime_fase2,
        ligar_fase2,
        desligar_fase2,
        enfileirar_tarefa as enfileirar_tarefa_fase2,
        listar_fila as listar_fila_fase2,
        limpar_fila as limpar_fila_fase2,
        status_fase2,
        relatorio_agora as relatorio_agora_fase2,
    )
    from core.backup_drive import status_backup_drive, sincronizar_backup_drive, restaurar_backup_drive
except Exception as e:
    registrar_erro(e)

try:
    from api.app import create_app

    app = create_app()
except Exception:
    app = None

try:
    from core.jarvis_chat_bridge import process_pending_tool_confirmation, try_jarvis_tool_flow
except Exception:
    def process_pending_tool_confirmation(texto, contexto=None, mode="normal"):
        return None

    def try_jarvis_tool_flow(texto, contexto=None, mode="normal"):
        return None

# Migração automática para camada segura de persistência.
try:
    carregar_memoria_usuario()
    carregar_aprendizado()
    status_admin()
except Exception:
    pass


# =========================
# CONTEXTO
# =========================
memoria_inicial = carregar_memoria_usuario()
contexto = {
    "nome_usuario": memoria_inicial.get("nome_usuario", ""),
    "idioma_preferido": memoria_inicial.get("idioma_preferido", "pt"),
    "tratamento": memoria_inicial.get("tratamento", ""),
    "ultima_intencao": "",
    "confirmacao_pendente": None,
    "jarvis_tool_pending": None,
    "admin_autenticado": False,
    "admin_usuario": "",
}


# =========================
# FUNÇÕES
# =========================
def saudacao():
    if contexto["nome_usuario"]:
        return f"Oi, {contexto['nome_usuario']}! Eu sou a NOVA."
    return "Oi! Eu sou a NOVA."


def sincronizar_memoria():
    memoria = carregar_memoria_usuario()
    memoria["nome_usuario"] = contexto.get("nome_usuario", "")
    memoria["idioma_preferido"] = contexto.get("idioma_preferido", "pt")
    memoria["tratamento"] = contexto.get("tratamento", "")
    salvar_memoria_usuario(memoria)


def comando_ensinar(texto):
    try:
        _, conteudo = texto.split(" ", 1)
        pergunta, resposta = conteudo.split("=", 1)

        pergunta = pergunta.strip()
        resposta = resposta.strip()

        total = salvar_aprendizado(pergunta, resposta)

        print(f"NOVA: Aprendi! ({total} respostas salvas)")
    except:
        print("NOVA: Use /ensinar pergunta = resposta")


def comando_google(texto):
    try:
        _, consulta = texto.split(" ", 1)
        url = f"https://www.google.com/search?q={quote_plus(consulta)}"

        wiki = gerar_pesquisa_wikipedia(consulta)

        if wiki:
            print(f"\nNOVA: {wiki['titulo']}\n{wiki['resumo']}")
        else:
            print("NOVA: Abrindo Google...")
            webbrowser.open(url)

    except:
        print("NOVA: Use /google algo")


def comando_nome(texto):
    try:
        _, nome = texto.split(" ", 1)
        contexto["nome_usuario"] = nome.strip().title()
        sincronizar_memoria()
        resposta = f"Beleza, vou te chamar de {contexto['nome_usuario']}"
        print(f"NOVA: {resposta}")
        registrar_interacao_usuario(texto, resposta)
    except:
        print("NOVA: Use /nome SeuNome")


def comando_memoria():
    memoria = carregar_memoria_usuario()
    resposta = formatar_memoria_usuario(memoria)
    print("NOVA:\n" + resposta)
    registrar_interacao_usuario("/memoria", resposta)


def comando_agente(texto):
    texto_norm = texto.lower()
    if texto_norm.startswith("/nova"):
        objetivo = texto[5:].strip(" :")
    elif texto_norm.startswith("/agente"):
        objetivo = texto[7:].strip(" :")
    else:
        objetivo = texto.strip()
    if not objetivo:
        print("NOVA: Use /nova <objetivo>. Exemplo: /nova organize meu dia: estudar, mercado, treino")
        return

    resultado = executar_agente(objetivo, contexto=contexto)
    contexto["confirmacao_pendente"] = resultado.get("confirmacao_pendente")
    sincronizar_memoria()
    resposta = resultado.get("mensagem", "Plano executado.")
    print("NOVA:", resposta)
    registrar_interacao_usuario(texto, resposta)


def comando_admin(texto):
    partes = texto.strip().split()
    if len(partes) == 1:
        print(
            "NOVA: Comandos admin -> /admin login <usuario> <senha> | /admin logout | "
            "/admin explicar | /admin status | /admin configurar <usuario> <senha>"
        )
        return

    acao = partes[1].lower()

    if acao == "login":
        if len(partes) < 4:
            print("NOVA: Use /admin login <usuario> <senha>")
            return
        usuario = partes[2]
        senha = partes[3]
        if autenticar_admin(usuario, senha):
            contexto["admin_autenticado"] = True
            contexto["admin_usuario"] = usuario
            print(f"NOVA: Login admin confirmado para {usuario}.")
        else:
            print("NOVA: Credenciais de admin inválidas.")
        return

    if acao == "logout":
        contexto["admin_autenticado"] = False
        contexto["admin_usuario"] = ""
        print("NOVA: Sessão admin encerrada.")
        return

    if acao == "status":
        print("NOVA:\n" + status_admin())
        return

    if acao == "configurar":
        if not contexto.get("admin_autenticado"):
            print("NOVA: Faça login admin antes de configurar credenciais.")
            return
        if len(partes) < 4:
            print("NOVA: Use /admin configurar <usuario> <senha>")
            return
        ok, mensagem = configurar_admin(partes[2], partes[3])
        print(f"NOVA: {mensagem}")
        if ok:
            contexto["admin_usuario"] = partes[2]
        return

    if acao == "explicar":
        if not contexto.get("admin_autenticado"):
            print("NOVA: Comando restrito. Faça /admin login primeiro.")
            return
        print("NOVA:\n" + explicacao_completa_admin())
        return

    if acao == "despertador":
        if not contexto.get("admin_autenticado"):
            print("NOVA: Comando restrito. Faça /admin login primeiro.")
            return

        if len(partes) == 2:
            print(
                "NOVA: /admin despertador status | /admin despertador ligar HH:MM [cidade] [nome] | "
                "/admin despertador desligar | /admin despertador testar"
            )
            return

        sub = partes[2].lower()
        if sub == "status":
            print("NOVA:\n" + status_despertador())
            return

        if sub == "ligar":
            if len(partes) < 4:
                print("NOVA: Use /admin despertador ligar HH:MM [cidade] [nome]")
                return
            hora = partes[3]
            cidade = None
            nome = None
            if len(partes) >= 5:
                cidade = partes[4]
            if len(partes) >= 6:
                nome = " ".join(partes[5:])
            ok, msg = configurar_despertador(hora=hora, cidade=cidade, saudacao_nome=nome, ativo=True)
            if ok:
                iniciar_monitor_despertador(
                    falar_callback=falar,
                    imprimir_callback=lambda m: print("NOVA (despertador):", m),
                )
            print("NOVA:", msg)
            return

        if sub == "desligar":
            print("NOVA:", desativar_despertador())
            return

        if sub == "testar":
            _, msg = disparar_despertador(
                falar_callback=falar,
                imprimir_callback=lambda m: print("NOVA (despertador):", m),
                forcar=True,
            )
            print("NOVA:", "Teste de despertador executado.")
            return

        print("NOVA: Subcomando de despertador não reconhecido.")
        return

    if acao == "jarvis2":
        if not contexto.get("admin_autenticado"):
            print("NOVA: Comando restrito. Faça /admin login primeiro.")
            return

        if len(partes) < 3:
            print(
                "NOVA: /admin jarvis2 status | /admin jarvis2 ligar [intervalo_min] | /admin jarvis2 desligar | "
                "/admin jarvis2 enfileirar <objetivo> | /admin jarvis2 fila | /admin jarvis2 limpar | "
                "/admin jarvis2 relatorio"
            )
            return

        sub = partes[2].lower()
        if sub == "status":
            print("NOVA:\n" + status_fase2())
            return
        if sub == "ligar":
            intervalo = 30
            if len(partes) >= 4:
                try:
                    intervalo = int(partes[3])
                except ValueError:
                    intervalo = 30
            iniciar_runtime_fase2(callback_notificacao=lambda m: (print("NOVA (JARVIS):", m), falar(m)))
            print("NOVA:", ligar_fase2(intervalo))
            return
        if sub == "desligar":
            print("NOVA:", desligar_fase2())
            return
        if sub == "enfileirar":
            if len(partes) < 4:
                print("NOVA: Use /admin jarvis2 enfileirar <objetivo>")
                return
            objetivo = " ".join(partes[3:])
            ok, msg = enfileirar_tarefa_fase2(objetivo, origem="admin_terminal")
            print("NOVA:", msg)
            return
        if sub == "fila":
            print("NOVA:\n" + listar_fila_fase2())
            return
        if sub == "limpar":
            print("NOVA:", limpar_fila_fase2())
            return
        if sub == "relatorio":
            print("NOVA:\n" + relatorio_agora_fase2())
            return
        print("NOVA: Subcomando jarvis2 não reconhecido.")
        return

    if acao == "drivebackup":
        if not contexto.get("admin_autenticado"):
            print("NOVA: Comando restrito. Faça /admin login primeiro.")
            return
        if len(partes) < 3:
            print("NOVA: /admin drivebackup status | /admin drivebackup sincronizar | /admin drivebackup restaurar")
            return
        sub = partes[2].lower()
        if sub == "status":
            print("NOVA:", status_backup_drive())
            return
        if sub == "sincronizar":
            ok, msg = sincronizar_backup_drive()
            print("NOVA:", msg)
            return
        if sub == "restaurar":
            ok, msg = restaurar_backup_drive()
            print("NOVA:", msg)
            return
        print("NOVA: Subcomando drivebackup não reconhecido.")
        return

    print("NOVA: Comando admin não reconhecido.")


# =========================
# LOOP PRINCIPAL
# =========================
def main():
    print("🤖 NOVA (modo terminal)")
    print(saudacao())
    print("Digite 'sair' para encerrar\n")

    iniciar_monitor_despertador(
        falar_callback=falar,
        imprimir_callback=lambda m: print("NOVA (despertador):", m),
    )
    iniciar_runtime_fase2(callback_notificacao=lambda m: (print("NOVA (JARVIS):", m), falar(m)))

    while True:
        user = input("Você: ").strip()

        if not user:
            continue

        if contexto.get("confirmacao_pendente"):
            resposta_confirmacao = processar_confirmacao_agente(user, contexto=contexto)
            if resposta_confirmacao:
                print("NOVA:", resposta_confirmacao)
                registrar_interacao_usuario(user, resposta_confirmacao)
                continue

        tool_confirmacao = process_pending_tool_confirmation(user, contexto, mode="normal")
        if isinstance(tool_confirmacao, dict) and tool_confirmacao.get("handled"):
            resposta = str(tool_confirmacao.get("reply", ""))
            print("NOVA:", resposta)
            registrar_interacao_usuario(user, resposta)
            continue

        if user.lower() == "sair":
            sincronizar_memoria()
            print("NOVA: Até mais! 👋")
            break

        # =========================
        # COMANDOS
        # =========================
        if user.startswith("/ensinar"):
            comando_ensinar(user)
            continue

        if user.startswith("/google"):
            comando_google(user)
            continue

        if user.startswith("/nome"):
            comando_nome(user)
            continue

        if user.startswith("/memoria"):
            comando_memoria()
            continue

        if user.startswith("/nova") or user.startswith("/agente"):
            comando_agente(user)
            continue

        if user.startswith("/admin"):
            comando_admin(user)
            continue

        if eh_pedido_de_agente(user):
            comando_agente(user)
            continue

        # =========================
        # CONVERSA NORMAL
        # =========================
        nome = extrair_nome_usuario(user)
        if nome:
            contexto["nome_usuario"] = nome
            sincronizar_memoria()

        jarvis_tool = try_jarvis_tool_flow(user, contexto, mode="normal")
        if isinstance(jarvis_tool, dict) and jarvis_tool.get("reply"):
            resposta = str(jarvis_tool.get("reply", ""))
            print("NOVA:", resposta)
            registrar_interacao_usuario(user, resposta)
            continue

        intencao = detectar_intencao(user, contexto)
        contexto["ultima_intencao"] = intencao
        resposta = responder(user, contexto=contexto)

        print("NOVA:", resposta)
        registrar_interacao_usuario(user, resposta)

        try:
            falar(resposta)
        except:
            pass


# =========================
# START
# =========================
if __name__ == "__main__":
    main()
