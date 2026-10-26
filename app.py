"""Entrada da aplicação; compõe o servidor sem efeitos ao importar a factory."""

from infrastructure.web import create_app

_app = None


def __getattr__(nome):
    global _app
    if nome != "app":
        raise AttributeError(nome)
    if _app is None:
        _app = create_app()
    return _app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
