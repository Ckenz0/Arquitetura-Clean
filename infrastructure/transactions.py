"""Transações em memória com estado compartilhado e restauração em caso de erro."""

from contextlib import contextmanager


class TransacaoMemoria:
    def __init__(self, livros, dados):
        self.livros = livros
        self.dados = dados
        self.lock = dados.lock
        self._profundidade = 0

    def snapshot(self):
        return {"livros": self.livros.exportar(), "estado": self.dados.exportar()}

    def restaurar(self, snapshot):
        self.livros.restaurar(snapshot["livros"])
        self.dados.restaurar(snapshot["estado"])

    def carregar(self):
        pass

    def confirmar(self, antes):
        pass

    @contextmanager
    def iniciar(self):
        with self.lock:
            if self._profundidade:
                self._profundidade += 1
                try:
                    yield
                finally:
                    self._profundidade -= 1
                return
            self.carregar()
            antes = self.snapshot()
            self._profundidade = 1
            try:
                yield
                self.confirmar(antes)
            except BaseException:
                self.restaurar(antes)
                raise
            finally:
                self._profundidade = 0
