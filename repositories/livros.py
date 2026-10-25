"""Armazenamento e consultas do catálogo em memória."""

from copy import deepcopy

from domain.regras import ErroLivraria


class RepositorioLivros:
    def __init__(self, livros=None):
        self._livros = deepcopy(livros or [])

    def todos(self):
        """Referências de trabalho para operações protegidas pelo serviço."""
        return tuple(self._livros)

    def obter(self, livro_id):
        for livro in self._livros:
            if livro["id"] == livro_id:
                return livro
        raise ErroLivraria("Livro não encontrado.", 404)

    def por_codigo(self, codigo):
        for livro in self._livros:
            if livro.get("codigo") == codigo:
                return livro
        raise ErroLivraria("Código de barras não encontrado.", 404)

    def _selecionar(self, campo, termo, parcial=False):
        termo = termo.strip().casefold()
        return [deepcopy(livro) for livro in self._livros
                if (termo in str(livro.get(campo, "")).casefold() if parcial
                    else termo == str(livro.get(campo, "")).casefold())]

    def buscar_por_titulo(self, titulo):
        return self._selecionar("titulo", titulo, parcial=True)

    def buscar_por_autor(self, autor):
        return self._selecionar("autor", autor, parcial=True)

    def filtrar_por_genero(self, genero):
        return self._selecionar("genero", genero)

    def consultar_estoque(self, titulo):
        livros = self.buscar_por_titulo(titulo)
        return livros[0].get("estoque", 0) if livros else 0

    def listar_lancamentos(self):
        return [deepcopy(livro) for livro in self._livros if livro.get("lancamento")]
