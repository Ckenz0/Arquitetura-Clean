"""Valor imutável de uma avaliação válida de livro."""

from dataclasses import dataclass

from .regras import ErroLivraria, texto_obrigatorio


@dataclass(frozen=True)
class Avaliacao:
    nota: int
    texto: str

    def __post_init__(self):
        if type(self.nota) is not int or not 1 <= self.nota <= 5:
            raise ErroLivraria("Escolha uma nota inteira de 1 a 5.")
        object.__setattr__(self, "texto", texto_obrigatorio(self.texto, "seu comentário"))
