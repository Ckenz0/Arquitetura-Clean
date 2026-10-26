"""Snapshot textual versionado e transações com substituição atômica do arquivo."""

from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock, RLock

from entities.regras import ErroLivraria

from .transactions import TransacaoMemoria

_locks = {}
_registro_lock = Lock()
_colecoes = {"clientes", "reservas", "acompanhamentos", "horarios", "eventos", "clubes"}


def lock_do_arquivo(arquivo):
    chave = os.path.normcase(str(Path(arquivo).resolve()))
    with _registro_lock:
        return _locks.setdefault(chave, RLock())


def _exigir(condicao):
    if not condicao:
        raise ValueError("Estrutura de dados incompatível.")


def _texto(valor):
    return isinstance(valor, str) and bool(valor.strip())


def _inteiro(valor):
    return type(valor) is int and valor >= 0


def _data(valor):
    _exigir(isinstance(valor, str))
    datetime.fromisoformat(valor)


def _avaliacao(valor, completa=False):
    _exigir(isinstance(valor, dict) and _texto(valor["cliente"]) and _texto(valor["texto"]))
    if completa or "nota" in valor:
        _exigir(type(valor["nota"]) is int and 1 <= valor["nota"] <= 5)
    if completa:
        _exigir(_texto(valor["id"]))
        _data(valor["data"])
        if "atualizada_em" in valor:
            _data(valor["atualizada_em"])


def _validar_livro(livro):
    _exigir(isinstance(livro, dict))
    _exigir(all(_texto(livro[c]) for c in ("id", "titulo", "autor", "genero")))
    _exigir(_inteiro(livro["estoque"]))
    _exigir(isinstance(livro.get("avaliacoes", []), list))
    for avaliacao in livro.get("avaliacoes", []):
        _avaliacao(avaliacao)


def _validar(snapshot):
    livros, estado = snapshot["livros"], snapshot["estado"]
    _exigir(isinstance(livros, list) and isinstance(estado, dict))
    ids = set()
    for livro in livros:
        _validar_livro(livro)
        _exigir(livro["id"] not in ids)
        ids.add(livro["id"])
    tabelas = estado["colecoes"]
    _exigir(isinstance(tabelas, dict) and set(tabelas) == _colecoes)
    for tabela in tabelas.values():
        _exigir(isinstance(tabela, dict) and all(_texto(k) for k in tabela))
    clientes = tabelas["clientes"]
    for chave, cliente in clientes.items():
        _exigir(isinstance(cliente, dict) and cliente["id"] == chave)
        for campo in ("generos", "desejos", "compras", "cupons", "notificacoes"):
            _exigir(isinstance(cliente[campo], list))
        _exigir(all(_texto(g) for g in cliente["generos"]))
        _exigir(all(d in ids for d in cliente["desejos"]))
        temas = cliente["temas_notificacao"]
        _exigir(temas is None or isinstance(temas, list) and all(_texto(t) for t in temas))
        for compra in cliente["compras"]:
            _exigir(isinstance(compra, dict))
            _validar_livro(compra["livro"])
            _exigir(_texto(compra["id"]) and _inteiro(compra["pontos"]))
            _exigir(compra["livro"]["id"] in ids and type(compra["_avisado"]) is bool)
            _data(compra["data"])
            for campo in ("expira_em", "avisar_em"):
                if compra[campo] is not None:
                    _data(compra[campo])
        for cupom in cliente["cupons"]:
            _exigir(_texto(cupom["codigo"]) and _texto(cupom["termos"]))
        for aviso in cliente["notificacoes"]:
            _exigir(all(_texto(aviso[c]) for c in ("id", "tema", "mensagem")))
            _data(aviso["data"])
    for chave, reserva in tabelas["reservas"].items():
        _exigir(reserva["id"] == chave and reserva["livro_id"] in ids)
        _exigir(reserva["cliente_id"] in clientes and _texto(reserva["titulo"]))
        _exigir(type(reserva["embrulho"]) is bool and reserva["status"] in {"pendente", "pronta", "cancelada"})
        _data(reserva["prazo"])
    for livro, interessados in tabelas["acompanhamentos"].items():
        _exigir(livro in ids and isinstance(interessados, set) and interessados <= clientes.keys())
    for chave, horario in tabelas["horarios"].items():
        _exigir(horario["id"] == chave and _texto(horario["livreiro"]))
        _exigir(horario["cliente_id"] is None or horario["cliente_id"] in clientes)
        _data(horario["quando"])
    for chave, evento in tabelas["eventos"].items():
        _exigir(evento["id"] == chave and _texto(evento["titulo"]) and _texto(evento["local"]))
        _exigir(evento["capacidade"] is None or _inteiro(evento["capacidade"]))
        _exigir(isinstance(evento["inscritos"], set) and evento["inscritos"] <= clientes.keys())
        _exigir(isinstance(evento["avisados"], set) and evento["avisados"] <= evento["inscritos"])
        _data(evento["quando"])
        if evento["lembrar_em"] is not None:
            _data(evento["lembrar_em"])
    for chave, clube in tabelas["clubes"].items():
        _exigir(clube["id"] == chave and _texto(clube["nome"]))
        _exigir(isinstance(clube["membros"], set) and clube["membros"] <= clientes.keys())
        _exigir(isinstance(clube["opinioes"], list))
        for opiniao in clube["opinioes"]:
            _exigir(opiniao["cliente"] in clube["membros"] and _texto(opiniao["texto"]))
    _exigir(isinstance(estado["fila"], list) and len(set(estado["fila"])) == len(estado["fila"]))
    _exigir(all(c in clientes for c in estado["fila"]))
    _exigir(_texto(estado["loja"]["horario"]) and _inteiro(estado["loja"]["lotacao"]))
    _exigir(isinstance(estado["avaliacoes"], list))
    chaves, publicos = set(), set()
    for registro in estado["avaliacoes"]:
        chave = (registro["livro_id"], registro["cliente_id"])
        _exigir(chave[0] in ids and chave[1] in clientes and chave not in chaves)
        _avaliacao(registro["avaliacao"], completa=True)
        _exigir(registro["avaliacao"]["id"] not in publicos)
        publicos.add(registro["avaliacao"]["id"])
        chaves.add(chave)


def _codificar(snapshot):
    _validar(snapshot)
    copia = deepcopy(snapshot)
    tabelas = copia["estado"]["colecoes"]
    tabelas["acompanhamentos"] = {k: sorted(v) for k, v in tabelas["acompanhamentos"].items()}
    for evento in tabelas["eventos"].values():
        for campo in ("inscritos", "avisados"):
            evento[campo] = sorted(evento[campo])
    for clube in tabelas["clubes"].values():
        clube["membros"] = sorted(clube["membros"])
    return {"versao": 1, **copia}


def _conjunto(valor):
    _exigir(isinstance(valor, list) and all(_texto(v) for v in valor))
    _exigir(len(set(valor)) == len(valor))
    return set(valor)


def _objeto(pares):
    resultado = {}
    for chave, valor in pares:
        _exigir(chave not in resultado)
        resultado[chave] = valor
    return resultado


def ler_txt(arquivo):
    try:
        bruto = json.loads(Path(arquivo).read_text(encoding="utf-8"), object_pairs_hook=_objeto,
            parse_constant=lambda valor: (_ for _ in ()).throw(ValueError("Número inválido.")))
        _exigir(isinstance(bruto, dict) and set(bruto) == {"versao", "livros", "estado"})
        _exigir(type(bruto["versao"]) is int and bruto["versao"] == 1)
        snapshot = {"livros": bruto["livros"], "estado": bruto["estado"]}
        tabelas = snapshot["estado"]["colecoes"]
        tabelas["acompanhamentos"] = {k: _conjunto(v) for k, v in tabelas["acompanhamentos"].items()}
        for evento in tabelas["eventos"].values():
            for campo in ("inscritos", "avisados"):
                evento[campo] = _conjunto(evento[campo])
        for clube in tabelas["clubes"].values():
            clube["membros"] = _conjunto(clube["membros"])
        _validar(snapshot)
        return snapshot
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as erro:
        raise ErroLivraria("Não foi possível ler os dados: arquivo inválido, incompatível ou indisponível.", 503) from erro


def gravar_atomico(arquivo, snapshot):
    temporario = None
    try:
        conteudo = json.dumps(_codificar(snapshot), ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        arquivo = Path(arquivo)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=arquivo.parent,
                                prefix=".livraria-", suffix=".tmp", delete=False) as saida:
            temporario = Path(saida.name)
            saida.write(conteudo)
            saida.flush()
            os.fsync(saida.fileno())
        os.replace(temporario, arquivo)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as erro:
        raise ErroLivraria("Não foi possível salvar os dados. Tente novamente.", 503) from erro
    finally:
        if temporario is not None and temporario.exists():
            temporario.unlink(missing_ok=True)


class TransacaoTxt(TransacaoMemoria):
    def __init__(self, arquivo, livros, dados):
        super().__init__(livros, dados)
        self.arquivo = Path(arquivo).resolve()
        self.lock = lock_do_arquivo(self.arquivo)
        self.dados.lock = self.lock
        with self.lock:
            self.carregar()

    def carregar(self):
        if self.arquivo.exists():
            self.restaurar(ler_txt(self.arquivo))

    def confirmar(self, antes):
        depois = self.snapshot()
        if depois != antes or not self.arquivo.exists():
            gravar_atomico(self.arquivo, depois)
