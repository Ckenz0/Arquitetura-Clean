"""HTTP Flask. As regras de negócio pertencem exclusivamente a livraria.py."""

from datetime import timedelta
import os
import secrets
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, session
from werkzeug.exceptions import HTTPException

from livraria import ErroLivraria, Livraria


def criar_demonstracao():
    """Dados ilustrativos da loja; os números não definem políticas comerciais."""
    livros = [
        {"id": "1984", "titulo": "1984", "autor": "George Orwell", "ano": 1949,
         "genero": "Distopia", "estoque": 3, "lancamento": False, "preco": 49.90,
         "codigo": "9788535914849", "secao": "Literatura", "prateleira": "A1",
         "sinopse": "Uma sociedade sob vigilância. Um clássico sobre liberdade, memória e poder.",
         "avaliacoes": [{"cliente": "Marina", "texto": "Uma leitura marcante."}]},
        {"id": "bichos", "titulo": "A Revolução dos Bichos", "autor": "George Orwell",
         "ano": 1945, "genero": "Distopia", "estoque": 2, "lancamento": False,
         "preco": 39.90, "codigo": "9788535909555", "secao": "Literatura", "prateleira": "A1",
         "sinopse": "Uma fábula sobre os animais de uma fazenda e os rumos de sua revolução.",
         "avaliacoes": [{"cliente": "Pedro", "texto": "Curto, envolvente e cheio de reflexões."}]},
        {"id": "hobbit", "titulo": "O Hobbit", "autor": "J.R.R. Tolkien", "ano": 1937,
         "genero": "Fantasia", "estoque": 5, "lancamento": False, "preco": 69.90,
         "codigo": "9788595084742", "secao": "Fantasia", "prateleira": "B2",
         "sinopse": "Bilbo Bolseiro deixa o conforto de casa para uma aventura inesperada.",
         "avaliacoes": [{"cliente": "Luiza", "texto": "Uma aventura para reler muitas vezes."}]},
        {"id": "reino", "titulo": "O Novo Reino", "autor": "Ana Silva", "ano": 2026,
         "genero": "Fantasia", "estoque": 4, "lancamento": True, "preco": 54.90,
         "codigo": "9780000000001", "secao": "Lançamentos", "prateleira": "L1",
         "sinopse": "Uma jornada por um reino que começa a descobrir suas próprias histórias.",
         "avaliacoes": []},
        {"id": "esgotado", "titulo": "Livro Esgotado", "autor": "Autor Exemplo", "ano": 2025,
         "genero": "Romance", "estoque": 0, "lancamento": False, "preco": 44.90,
         "codigo": "9780000000002", "secao": "Romances", "prateleira": "C3",
         "sinopse": "Um título de demonstração para acompanhar a reposição de estoque.",
         "avaliacoes": []},
    ]
    loja = Livraria(livros)
    loja.configurar_loja("Seg–Sáb, 09h às 19h", 12)
    agora = loja.agora()
    loja.oferecer_horario("Carlos · Literatura e clássicos", (agora + timedelta(days=1)).isoformat())
    loja.oferecer_horario("Lia · Fantasia e ficção", (agora + timedelta(days=2)).isoformat())
    loja.cadastrar_evento("Conversa com autores", (agora + timedelta(days=3)).isoformat(),
                         "Salão da livraria", capacidade=20,
                         lembrar_em=(agora + timedelta(days=2)).isoformat())
    loja.cadastrar_evento("Encontro do clube de leitura", (agora + timedelta(days=7)).isoformat(),
                         "Sala de leitura", capacidade=12,
                         lembrar_em=(agora + timedelta(days=6)).isoformat())
    loja.criar_clube("Leituras compartilhadas")
    return loja


def create_app(livraria=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    app.json.ensure_ascii = False
    demonstracao = livraria is None
    loja = criar_demonstracao() if demonstracao else livraria
    app.extensions["livraria"] = loja

    @app.before_request
    def identificar_cliente():
        # Mesmo ações sem campos precisam recusar um corpo malformado.
        # Requisições sem corpo continuam válidas para essas ações.
        if (request.endpoint and request.path.startswith("/api/")
            and request.method in {"POST", "PATCH"} and request.get_data(cache=True)):
            dados()
        if "cliente_id" not in session:
            session["cliente_id"] = uuid4().hex
            if demonstracao:
                # Entradas fictícias do caixa para tornar histórico e fidelidade visíveis.
                agora = loja.agora()
                loja.registrar_compra(session["cliente_id"], "1984", 20,
                                      expira_em=(agora + timedelta(days=3)).isoformat(),
                                      avisar_em=agora.isoformat())
                loja.conceder_cupom(session["cliente_id"], "BOASLEITURAS",
                                   "Cupom ilustrativo: consulte as condições no caixa.")

    def cliente():
        return session["cliente_id"]

    def dados(*obrigatorios):
        if not request.is_json:
            raise ErroLivraria("Envie um objeto JSON.")
        corpo = request.get_json()
        if not isinstance(corpo, dict):
            raise ErroLivraria("Envie um objeto JSON.")
        for campo in obrigatorios:
            if not isinstance(corpo.get(campo), str) or not corpo[campo].strip():
                raise ErroLivraria(f"Informe {campo}.")
        return corpo

    @app.errorhandler(ErroLivraria)
    def erro_dominio(erro):
        return jsonify(erro=str(erro)), erro.status

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        mensagens = {400: "Requisição inválida. Confira o JSON enviado.",
                     404: "Recurso não encontrado.", 405: "Método não permitido.",
                     413: "Requisição muito grande.", 415: "Envie um objeto JSON."}
        return jsonify(erro=mensagens.get(erro.code, "Não foi possível atender à requisição.")), erro.code

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/estado")
    def estado():
        return jsonify(loja.estado(cliente()))

    @app.get("/api/livros")
    def livros():
        return jsonify(loja.buscar(request.args.get("q", ""), request.args.get("genero", ""),
                                  request.args.get("lancamentos") == "1"))

    @app.get("/api/livros/<livro_id>")
    def livro(livro_id):
        return jsonify(loja.livro(livro_id))

    @app.get("/api/codigo/<codigo>")
    def codigo(codigo):
        return jsonify(loja.por_codigo(codigo))

    @app.post("/api/avisos-estoque")
    def avisos_estoque():
        corpo = dados("livro_id")
        return jsonify(loja.acompanhar_estoque(cliente(), corpo["livro_id"])), 201

    @app.post("/api/reservas")
    def reservar():
        corpo = dados("livro_id", "prazo")
        return jsonify(loja.reservar(cliente(), corpo["livro_id"], corpo["prazo"],
                                    corpo.get("embrulho", False))), 201

    @app.patch("/api/reservas/<reserva_id>")
    def alterar_reserva(reserva_id):
        return jsonify(loja.alterar_prazo(cliente(), reserva_id, dados("prazo")["prazo"]))

    @app.post("/api/reservas/<reserva_id>/cancelar")
    def cancelar(reserva_id):
        return jsonify(loja.cancelar_reserva(cliente(), reserva_id))

    @app.post("/api/fila")
    def fila():
        return jsonify(loja.entrar_fila(cliente())), 201

    @app.post("/api/agendamentos")
    def agendar():
        return jsonify(loja.agendar(cliente(), dados("horario_id")["horario_id"])), 201

    @app.post("/api/eventos/<evento_id>/inscricoes")
    def inscrever(evento_id):
        return jsonify(loja.inscrever(cliente(), evento_id)), 201

    @app.post("/api/clubes/<clube_id>/participar")
    def participar(clube_id):
        return jsonify(loja.participar_clube(cliente(), clube_id)), 201

    @app.post("/api/clubes/<clube_id>/opinioes")
    def opinar(clube_id):
        return jsonify(loja.publicar_opiniao(cliente(), clube_id, dados("texto")["texto"])), 201

    @app.post("/api/desejos")
    def desejo():
        return jsonify(loja.adicionar_desejo(cliente(), dados("livro_id")["livro_id"])), 201

    @app.patch("/api/preferencias")
    def preferencias():
        corpo = dados()
        if not corpo or set(corpo) - {"generos", "temas_notificacao"}:
            raise ErroLivraria("Informe gêneros e/ou temas de notificação.")
        return jsonify(loja.preferencias(cliente(), **corpo))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
