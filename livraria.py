"""Compatibilidade dos exemplos anteriores; o Model está em models.livraria."""

from models.livraria import (
    Catalogo,
    ErroLivraria,
    Livraria,
    RepositorioLivros,
    filtrar_livros,
)

__all__ = [
    "Catalogo", "ErroLivraria", "Livraria", "RepositorioLivros", "filtrar_livros",
]
