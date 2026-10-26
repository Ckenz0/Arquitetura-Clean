"""Validações e políticas compartilhadas pelos casos de uso da livraria."""

from copy import deepcopy
from datetime import datetime

NAO_INFORMADO = object()
TEMAS = {"estoque", "reservas", "fidelidade", "eventos"}


class ErroLivraria(ValueError):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


def inteiro_nao_negativo(valor, campo):
    if type(valor) is not int or valor < 0:
        raise ErroLivraria(f"{campo} deve ser um inteiro não negativo.")
    return valor


def texto_obrigatorio(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise ErroLivraria(f"Informe {campo}.")
    return valor.strip()


def data_iso(valor, agora, futuro=False):
    try:
        data = datetime.fromisoformat(texto_obrigatorio(valor, "uma data ISO válida"))
        if data.tzinfo is None:
            data = data.astimezone()
    except (ValueError, TypeError, OSError, OverflowError):
        raise ErroLivraria("Informe uma data e hora válidas.") from None
    if futuro and data <= agora():
        raise ErroLivraria("A data deve estar no futuro.")
    return data


def validar_reserva(estoque, embrulho):
    if type(embrulho) is not bool:
        raise ErroLivraria("Embrulho deve ser verdadeiro ou falso.")
    if estoque <= 0:
        raise ErroLivraria("Livro sem exemplares disponíveis.", 409)


def validar_preferencias(generos, temas_notificacao):
    for valor, campo in [(generos, "Gêneros"), (temas_notificacao, "Temas")]:
        if valor is NAO_INFORMADO or (campo == "Temas" and valor is None):
            continue
        if not isinstance(valor, list) or any(not isinstance(v, str) or not v.strip() for v in valor):
            raise ErroLivraria(f"{campo} deve ser uma lista de textos.")
    if temas_notificacao is not NAO_INFORMADO and temas_notificacao is not None:
        if not set(temas_notificacao).issubset(TEMAS):
            raise ErroLivraria("Tema de notificação inválido.")


def filtrar_livros(livros, **criterios):
    """Filtra por correspondência exata, combinando todos os critérios."""
    return [deepcopy(livro) for livro in livros
            if all(livro.get(campo) == valor for campo, valor in criterios.items())]
