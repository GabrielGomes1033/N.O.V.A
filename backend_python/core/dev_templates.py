from __future__ import annotations


HTML_BASICO = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sistema criado pela NOVA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="container">
    <h1>Sistema criado pela NOVA</h1>
    <p>Projeto inicial gerado automaticamente para você começar mais rápido.</p>
    <button type="button" onclick="mensagem()">Testar sistema</button>
  </main>

  <script src="script.js"></script>
</body>
</html>
"""


CSS_BASICO = """* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: Arial, sans-serif;
  background: linear-gradient(135deg, #0f172a, #1e293b);
  color: #ffffff;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.container {
  width: min(100%, 680px);
  padding: 32px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.92);
  text-align: center;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
}

h1 {
  margin-bottom: 12px;
}

p {
  color: #cbd5e1;
  line-height: 1.6;
}

button {
  margin-top: 24px;
  padding: 14px 22px;
  border: none;
  border-radius: 10px;
  background: #38bdf8;
  color: #082f49;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}
"""


JS_BASICO = """function mensagem() {
  alert("Sistema funcionando!");
}
"""


API_FLASK = """from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify(
        {
            "status": "online",
            "mensagem": "API criada pela NOVA",
        }
    )


@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    return jsonify(
        [
            {"id": 1, "nome": "Gabriel"},
            {"id": 2, "nome": "NOVA"},
        ]
    )


@app.route("/usuarios", methods=["POST"])
def criar_usuario():
    dados = request.get_json(silent=True) or {}
    return jsonify(
        {
            "mensagem": "Usuário criado com sucesso",
            "dados": dados,
        }
    ), 201


if __name__ == "__main__":
    app.run(debug=True)
"""


API_FASTAPI = """from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="API criada pela NOVA")


class Usuario(BaseModel):
    nome: str


@app.get("/")
def home():
    return {"status": "online", "mensagem": "API criada pela NOVA"}


@app.get("/usuarios")
def listar_usuarios():
    return [{"id": 1, "nome": "Gabriel"}, {"id": 2, "nome": "NOVA"}]


@app.post("/usuarios", status_code=201)
def criar_usuario(usuario: Usuario):
    return {"mensagem": "Usuário criado com sucesso", "dados": usuario.model_dump()}
"""


REQUIREMENTS_FLASK = """flask
"""


REQUIREMENTS_FASTAPI = """fastapi
uvicorn
"""


API_FLASK_SQLITE = """from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)
DB_NAME = "nova.sqlite3"


def conectar():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_banco():
    conn = conectar()
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 0
        )
        '''
    )
    conn.commit()
    conn.close()


@app.route("/")
def home():
    return jsonify({"status": "online", "mensagem": "API SQLite criada pela NOVA"})


@app.route("/produtos", methods=["GET"])
def listar_produtos():
    conn = conectar()
    rows = conn.execute("SELECT id, nome, quantidade FROM produtos ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/produtos", methods=["POST"])
def criar_produto():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()
    quantidade = int(dados.get("quantidade", 0) or 0)

    if not nome:
        return jsonify({"erro": "nome_obrigatorio"}), 400

    conn = conectar()
    cursor = conn.execute(
        "INSERT INTO produtos (nome, quantidade) VALUES (?, ?)",
        (nome, quantidade),
    )
    conn.commit()
    produto_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": produto_id, "nome": nome, "quantidade": quantidade}), 201


if __name__ == "__main__":
    inicializar_banco()
    app.run(debug=True)
"""


REQUIREMENTS_FLASK_SQLITE = """flask
"""


README_SITE = """# Sistema criado pela NOVA

Este projeto web foi gerado automaticamente pela assistente NOVA.

## Como executar

Abra o arquivo `index.html` no navegador.
"""


README_API = """# API criada pela NOVA

Este projeto foi gerado automaticamente pela assistente NOVA.

## Como executar

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Flask

```bash
python app.py
```

## FastAPI

```bash
uvicorn app:app --reload
```
"""


README_API_DB = """# API com banco de dados criada pela NOVA

Este projeto inicial usa Flask com SQLite para facilitar testes locais.

## Como executar

```bash
pip install -r requirements.txt
python app.py
```

## Rotas iniciais

- `GET /`
- `GET /produtos`
- `POST /produtos`
"""


LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login - NOVA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="login-shell">
    <form class="login-card">
      <h1>Login</h1>

      <label for="email">E-mail</label>
      <input id="email" name="email" type="email" placeholder="Digite seu e-mail" required>

      <label for="senha">Senha</label>
      <input id="senha" name="senha" type="password" placeholder="Digite sua senha" required>

      <button type="button" onclick="login()">Entrar</button>
      <p id="feedback"></p>
    </form>
  </main>

  <script src="script.js"></script>
</body>
</html>
"""


LOGIN_CSS = """* {
  box-sizing: border-box;
}

body {
  min-height: 100vh;
  margin: 0;
  font-family: Arial, sans-serif;
  background: linear-gradient(135deg, #0f172a, #1e293b);
}

.login-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-card {
  width: min(100%, 360px);
  padding: 32px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(10px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
  color: #ffffff;
}

h1 {
  margin: 0 0 20px;
}

label {
  display: block;
  margin-top: 14px;
  margin-bottom: 6px;
  font-size: 14px;
}

input,
button {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 10px;
}

input {
  background: #f8fafc;
  color: #0f172a;
}

button {
  margin-top: 18px;
  background: #38bdf8;
  color: #082f49;
  font-weight: 700;
  cursor: pointer;
}

#feedback {
  min-height: 20px;
  margin-top: 14px;
  color: #bae6fd;
}
"""


LOGIN_JS = """function login() {
  const email = document.getElementById("email").value.trim();
  const senha = document.getElementById("senha").value.trim();
  const feedback = document.getElementById("feedback");

  if (!email || !senha) {
    feedback.textContent = "Preencha e-mail e senha para continuar.";
    return;
  }

  feedback.textContent = "Interface pronta. Agora conecte este login ao backend.";
}
"""


ESTOQUE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Estoque - NOVA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="page">
    <section class="card">
      <h1>Controle de estoque</h1>
      <p>Cadastre produtos para começar a montar seu sistema.</p>

      <div class="grid">
        <input id="produto" type="text" placeholder="Nome do produto">
        <input id="quantidade" type="number" min="0" placeholder="Quantidade">
        <button type="button" onclick="adicionarProduto()">Adicionar item</button>
      </div>

      <table>
        <thead>
          <tr>
            <th>Produto</th>
            <th>Quantidade</th>
          </tr>
        </thead>
        <tbody id="lista-estoque"></tbody>
      </table>
    </section>
  </main>

  <script src="script.js"></script>
</body>
</html>
"""


ESTOQUE_CSS = """* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: #020617;
  color: #e2e8f0;
}

.page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  padding: 32px 18px;
}

.card {
  width: min(100%, 820px);
  background: #0f172a;
  border-radius: 20px;
  padding: 28px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
}

.grid {
  display: grid;
  grid-template-columns: 2fr 1fr auto;
  gap: 12px;
  margin: 24px 0;
}

input,
button {
  padding: 12px;
  border-radius: 10px;
  border: none;
}

button {
  background: #22c55e;
  color: #052e16;
  font-weight: 700;
  cursor: pointer;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 14px 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  text-align: left;
}
"""


ESTOQUE_JS = """const estoque = [];

function renderizarEstoque() {
  const tbody = document.getElementById("lista-estoque");
  tbody.innerHTML = "";

  estoque.forEach((item) => {
    const linha = document.createElement("tr");
    linha.innerHTML = `<td>${item.nome}</td><td>${item.quantidade}</td>`;
    tbody.appendChild(linha);
  });
}

function adicionarProduto() {
  const produto = document.getElementById("produto");
  const quantidade = document.getElementById("quantidade");

  const nome = produto.value.trim();
  const qtd = Number(quantidade.value);

  if (!nome || Number.isNaN(qtd)) {
    alert("Preencha o nome do produto e a quantidade.");
    return;
  }

  estoque.push({ nome, quantidade: qtd });
  produto.value = "";
  quantidade.value = "";
  renderizarEstoque();
}
"""


README_ESTOQUE = """# Sistema de estoque criado pela NOVA

Este projeto inicial foi gerado automaticamente para servir como base de um controle de estoque.

## O que já vem pronto

- Tela HTML com formulário simples
- Tabela de itens
- JavaScript para cadastro local

## Próximos passos

1. Conectar a um backend
2. Salvar os itens em banco de dados
3. Adicionar entrada, saída e relatórios
"""


ADMIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Painel Administrativo - NOVA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="dashboard">
    <header class="hero">
      <div>
        <p class="eyebrow">PAINEL ADMINISTRATIVO</p>
        <h1>NOVA Control Center</h1>
        <p>Base visual para gerenciar usuários, métricas e módulos do sistema.</p>
      </div>
      <button type="button" onclick="notificar()">Verificar status</button>
    </header>

    <section class="cards">
      <article class="card">
        <h2>Usuários ativos</h2>
        <strong>128</strong>
        <span>+12 hoje</span>
      </article>
      <article class="card">
        <h2>Pedidos processados</h2>
        <strong>842</strong>
        <span>Fluxo estável</span>
      </article>
      <article class="card">
        <h2>Saúde do sistema</h2>
        <strong>98%</strong>
        <span>Sem alertas críticos</span>
      </article>
    </section>
  </main>

  <script src="script.js"></script>
</body>
</html>
"""


ADMIN_CSS = """* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: radial-gradient(circle at top, #12324a 0%, #020617 58%);
  color: #f8fafc;
}

.dashboard {
  width: min(1100px, 100%);
  margin: 0 auto;
  padding: 32px 20px 48px;
}

.hero {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  border-radius: 24px;
  background: rgba(15, 23, 42, 0.86);
  border: 1px solid rgba(56, 189, 248, 0.22);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.28);
}

.eyebrow {
  letter-spacing: 0.3em;
  font-size: 12px;
  color: #67e8f9;
}

h1 {
  margin: 8px 0 12px;
  font-size: clamp(28px, 4vw, 42px);
}

button {
  border: none;
  border-radius: 14px;
  padding: 14px 18px;
  background: #22d3ee;
  color: #083344;
  font-weight: 700;
  cursor: pointer;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin-top: 24px;
}

.card {
  padding: 22px;
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.card h2 {
  margin-top: 0;
  font-size: 16px;
  color: #cbd5e1;
}

.card strong {
  display: block;
  margin: 14px 0 8px;
  font-size: 36px;
}

.card span {
  color: #67e8f9;
}
"""


ADMIN_JS = """function notificar() {
  alert("Painel pronto. Agora conecte os dados reais do backend.");
}
"""


README_ADMIN = """# Painel administrativo criado pela NOVA

Esta base visual foi gerada para acelerar a construção de um dashboard administrativo.

## Próximos passos

1. Conectar métricas reais da API
2. Adicionar autenticação
3. Integrar gráficos e tabelas
"""
