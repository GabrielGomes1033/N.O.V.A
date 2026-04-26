from flask import Flask, jsonify, request

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
