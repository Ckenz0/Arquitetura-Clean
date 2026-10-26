"""Composição externa dos casos de uso e seus adaptadores."""

from interface_adapters.repositories import RepositorioEstado, RepositorioLivros
from use_cases.livraria import Catalogo, Livraria as CasoDeUsoLivraria

from .transactions import TransacaoMemoria


class Livraria(CasoDeUsoLivraria):
    """Fachada compatível que fornece adaptadores padrão fora do núcleo."""

    def __init__(self, livros=None, agora=None, *, repositorio=None, dados=None, transacao=None):
        catalogo = repositorio if repositorio is not None else RepositorioLivros(livros)
        estado = dados if dados is not None else RepositorioEstado()
        unidade = transacao if transacao is not None else TransacaoMemoria(catalogo, estado)
        super().__init__(catalogo, estado, unidade, agora=agora)


def criar_persistente(arquivo, *, agora=None):
    from demonstracao import livros_iniciais, preencher_demonstracao
    from .txt import TransacaoTxt

    livros, dados = RepositorioLivros(), RepositorioEstado()
    transacao = TransacaoTxt(arquivo, livros, dados)
    loja = Livraria(repositorio=livros, dados=dados, transacao=transacao, agora=agora)
    with transacao.iniciar():
        if not transacao.arquivo.exists():
            livros.restaurar(livros_iniciais())
            preencher_demonstracao(loja)
    return loja
