"""Armazenamento e consultas do catálogo em memória."""

from copy import deepcopy

from entities.regras import ErroLivraria


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

    def exportar(self):
        return deepcopy(self._livros)

    def restaurar(self, livros):
        self._livros = deepcopy(livros)


"""Estado em memória compartilhado pelas operações de uma instância da loja."""

from copy import deepcopy
from threading import RLock


class RepositorioEstado:
    def __init__(self):
        self.lock = RLock()
        self._colecoes = {nome: {} for nome in (
            "clientes", "reservas", "acompanhamentos", "horarios", "eventos", "clubes",
        )}
        self._fila = []
        self._loja = {"horario": "Não informado", "lotacao": 0}
        self._avaliacoes = {}

    def obter(self, colecao, identificador, padrao=None):
        """Obtém a referência de trabalho usada dentro da operação atômica."""
        return self._colecoes[colecao].get(identificador, padrao)

    def salvar(self, colecao, identificador, valor):
        self._colecoes[colecao][identificador] = valor

    def listar(self, colecao):
        return tuple(self._colecoes[colecao].values())

    def obter_ou_criar(self, colecao, identificador, padrao):
        return self._colecoes[colecao].setdefault(identificador, padrao)

    def fila(self):
        return self._fila

    def configurar_loja(self, horario, lotacao):
        self._loja = {"horario": horario, "lotacao": lotacao}

    def informacoes_loja(self):
        return deepcopy(self._loja)

    def obter_avaliacao(self, livro_id, cliente_id):
        return deepcopy(self._avaliacoes.get((livro_id, cliente_id)))

    def salvar_avaliacao(self, livro_id, cliente_id, avaliacao):
        self._avaliacoes[(livro_id, cliente_id)] = deepcopy(avaliacao)

    def listar_avaliacoes(self, livro_id):
        return [deepcopy(avaliacao) for (livro, _), avaliacao in self._avaliacoes.items()
                if livro == livro_id]

    def exportar(self):
        return deepcopy({
            "colecoes": self._colecoes, "fila": self._fila, "loja": self._loja,
            "avaliacoes": [
                {"livro_id": livro, "cliente_id": cliente, "avaliacao": avaliacao}
                for (livro, cliente), avaliacao in self._avaliacoes.items()
            ],
        })

    def restaurar(self, estado):
        estado = deepcopy(estado)
        self._colecoes = estado["colecoes"]
        self._fila = estado["fila"]
        self._loja = estado["loja"]
        self._avaliacoes = {
            (r["livro_id"], r["cliente_id"]): r["avaliacao"] for r in estado["avaliacoes"]
        }
