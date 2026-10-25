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
