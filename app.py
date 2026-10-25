"""Configura e conecta as camadas da aplicação da livraria."""

import os
import secrets

from flask import Flask

from controllers import registrar_controladores
from demonstracao import criar_demonstracao


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

    registrar_controladores(app, demonstracao=demonstracao)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
