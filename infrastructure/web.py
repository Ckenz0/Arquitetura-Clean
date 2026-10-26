"""Factory Flask e configuração externa da persistência e da sessão."""

import os
from pathlib import Path
import secrets

from flask import Flask

from entities.regras import ErroLivraria
from interface_adapters.http import registrar_controladores

from .composition import criar_persistente
from .txt import lock_do_arquivo

PADRAO = object()
RAIZ = Path(__file__).resolve().parent.parent


def _chave_local(arquivo):
    chave = Path(arquivo).parent / "chave_sessao.key"
    try:
        with lock_do_arquivo(chave):
            if not chave.exists():
                chave.parent.mkdir(parents=True, exist_ok=True)
                with chave.open("x", encoding="ascii") as saida:
                    saida.write(secrets.token_hex(32))
            valor = chave.read_text(encoding="ascii").strip()
            if len(valor) != 64 or any(c not in "0123456789abcdef" for c in valor):
                raise ValueError("Chave local inválida.")
            return valor
    except (OSError, ValueError) as erro:
        raise ErroLivraria("Não foi possível carregar a chave local da sessão.", 503) from erro


def create_app(livraria=None, *, arquivo_dados=PADRAO):
    demonstracao = livraria is None
    caminho = None
    if livraria is not None:
        loja = livraria
    elif arquivo_dados is None:
        from demonstracao import criar_demonstracao
        loja = criar_demonstracao()
    else:
        caminho = Path(os.environ.get("LIVRARIA_ARQUIVO_DADOS") or RAIZ / "instance/livraria.txt") if arquivo_dados is PADRAO else Path(arquivo_dados)
        loja = criar_persistente(caminho)
    chave = os.environ.get("SECRET_KEY")
    if not chave:
        chave = _chave_local(caminho) if caminho is not None else secrets.token_hex(32)
    app = Flask(__name__, template_folder=str(RAIZ / "templates"), static_folder=str(RAIZ / "static"))
    app.config.update(
        SECRET_KEY=chave, SESSION_COOKIE_NAME="entrelinhas_clean",
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1024 * 1024,
        LIVRARIA_ARQUIVO_DADOS=str(caminho) if caminho is not None else None,
    )
    app.json.ensure_ascii = False
    app.extensions["livraria"] = loja
    registrar_controladores(app, demonstracao=demonstracao)
    return app
