"""Coordenação dos casos de uso, regras de domínio e repositórios."""

from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4

from domain.avaliacao import Avaliacao
from domain.regras import (
    ErroLivraria, NAO_INFORMADO, data_iso, inteiro_nao_negativo,
    texto_obrigatorio, validar_preferencias, validar_reserva,
)
from repositories import RepositorioEstado, RepositorioLivros


class Catalogo:
    """Consultas de catálogo fornecidas pelo repositório de livros."""

    def __init__(self, repositorio):
        self.repositorio = repositorio

    def buscar_por_titulo(self, titulo):
        return self.repositorio.buscar_por_titulo(titulo)

    def buscar_por_autor(self, autor):
        return self.repositorio.buscar_por_autor(autor)

    def filtrar_por_genero(self, genero):
        return self.repositorio.filtrar_por_genero(genero)

    def consultar_estoque(self, titulo):
        return self.repositorio.consultar_estoque(titulo)

    def listar_lancamentos(self):
        return self.repositorio.listar_lancamentos()


def atomico(metodo):
    """Serializa operações compostas sobre os dados deste processo."""
    @wraps(metodo)
    def executar(self, *args, **kwargs):
        with self._lock:
            return metodo(self, *args, **kwargs)
    return executar


class Livraria(Catalogo):
    def __init__(self, livros=None, agora=None, *, repositorio=None, dados=None):
        super().__init__(repositorio if repositorio is not None else RepositorioLivros(livros))
        self.agora = agora or (lambda: datetime.now(timezone.utc))
        self.dados = dados if dados is not None else RepositorioEstado()
        self._lock = self.dados.lock

    def _cliente(self, cliente_id):
        texto_obrigatorio(cliente_id, "o identificador do cliente")
        cliente = self.dados.obter("clientes", cliente_id)
        if cliente is None:
            cliente = {
                "id": cliente_id, "generos": [], "temas_notificacao": None,
                "desejos": [], "compras": [], "cupons": [], "notificacoes": [],
            }
            self.dados.salvar("clientes", cliente_id, cliente)
        return cliente

    def _data(self, valor, futuro=False):
        return data_iso(valor, self.agora, futuro=futuro)

    def _notificar(self, cliente_id, tema, mensagem):
        cliente = self._cliente(cliente_id)
        temas = cliente["temas_notificacao"]
        if temas is None or tema in temas:
            cliente["notificacoes"].append({
                "id": uuid4().hex, "tema": tema, "mensagem": mensagem,
                "data": self.agora().isoformat(),
            })

    def _recurso(self, colecao, identificador, nome):
        try:
            recurso = self.dados.obter(colecao, identificador)
        except TypeError:
            recurso = None
        if recurso is None:
            raise ErroLivraria(f"{nome} não encontrado.", 404)
        return recurso

    def _reserva(self, reserva_id, cliente_id=None):
        reserva = self._recurso("reservas", reserva_id, "Reserva")
        if cliente_id is not None and reserva["cliente_id"] != cliente_id:
            raise ErroLivraria("Reserva não encontrada.", 404)
        return reserva

    def _livro(self, livro_id):
        return self.repositorio.obter(livro_id)

    @atomico
    def livro(self, livro_id, cliente_id=None):
        livro = deepcopy(self._livro(livro_id))
        novas = self.dados.listar_avaliacoes(livro_id)
        if novas:
            livro.setdefault("avaliacoes", []).extend(novas)
        if cliente_id is not None:
            livro["ja_avaliou"] = self.dados.obter_avaliacao(livro_id, cliente_id) is not None
        return livro

    @atomico
    def por_codigo(self, codigo):
        return self.livro(self.repositorio.por_codigo(codigo)["id"])

    @atomico
    def buscar(self, q="", genero="", lancamentos=False):
        termo = q.strip().casefold()
        return [self.livro(livro["id"]) for livro in self.repositorio.todos()
                if (not termo or termo in livro["titulo"].casefold()
                    or termo in livro["autor"].casefold())
                and (not genero or genero.casefold() == livro["genero"].casefold())
                and (not lancamentos or livro.get("lancamento"))]

    @atomico
    def reservar(self, cliente_id, livro_id, prazo, embrulho=False):
        livro = self._livro(livro_id)
        data = self._data(prazo, futuro=True)
        validar_reserva(livro["estoque"], embrulho)
        self._cliente(cliente_id)
        reserva = {
            "id": uuid4().hex, "cliente_id": cliente_id,
            "livro_id": livro_id, "titulo": livro["titulo"],
            "prazo": data.isoformat(), "embrulho": embrulho, "status": "pendente",
        }
        livro["estoque"] -= 1
        self.dados.salvar("reservas", reserva["id"], reserva)
        return deepcopy(reserva)

    @atomico
    def reservas(self, cliente_id):
        return [deepcopy(r) for r in self.dados.listar("reservas") if r["cliente_id"] == cliente_id]

    @atomico
    def alterar_prazo(self, cliente_id, reserva_id, prazo):
        reserva = self._reserva(reserva_id, cliente_id)
        data = self._data(prazo, futuro=True)
        if reserva["status"] == "cancelada":
            raise ErroLivraria("A reserva já foi cancelada.", 409)
        reserva["prazo"] = data.isoformat()
        return deepcopy(reserva)

    @atomico
    def cancelar_reserva(self, cliente_id, reserva_id):
        reserva = self._reserva(reserva_id, cliente_id)
        if reserva["status"] != "cancelada":
            livro = self._livro(reserva["livro_id"])
            self.atualizar_estoque(livro["id"], livro["estoque"] + 1)
            reserva["status"] = "cancelada"
        return deepcopy(reserva)

    @atomico
    def marcar_pronta(self, reserva_id):
        reserva = self._reserva(reserva_id)
        if reserva["status"] == "cancelada":
            raise ErroLivraria("A reserva já foi cancelada.", 409)
        if reserva["status"] != "pronta":
            reserva["status"] = "pronta"
            self._notificar(reserva["cliente_id"], "reservas",
                            f'Sua reserva de {reserva["titulo"]} está pronta para retirada.')
        return deepcopy(reserva)

    @atomico
    def acompanhar_estoque(self, cliente_id, livro_id):
        self._livro(livro_id)
        self._cliente(cliente_id)
        self.dados.obter_ou_criar("acompanhamentos", livro_id, set()).add(cliente_id)
        return {"livro_id": livro_id, "acompanhando": True}

    @atomico
    def atualizar_estoque(self, livro_id, quantidade):
        inteiro_nao_negativo(quantidade, "Estoque")
        livro = self._livro(livro_id)
        anterior = livro["estoque"]
        livro["estoque"] = quantidade
        if anterior == 0 and quantidade > 0:
            for cliente_id in self.dados.obter("acompanhamentos", livro_id, set()):
                self._notificar(cliente_id, "estoque", f'{livro["titulo"]} voltou ao estoque.')
        return deepcopy(livro)

    @atomico
    def notificacoes(self, cliente_id):
        return deepcopy(self._cliente(cliente_id)["notificacoes"])

    @atomico
    def preferencias(self, cliente_id, generos=NAO_INFORMADO,
                     temas_notificacao=NAO_INFORMADO):
        validar_preferencias(generos, temas_notificacao)
        cliente = self._cliente(cliente_id)
        if generos is not NAO_INFORMADO:
            cliente["generos"] = list(dict.fromkeys(g.strip() for g in generos))
        if temas_notificacao is not NAO_INFORMADO:
            cliente["temas_notificacao"] = (None if temas_notificacao is None
                                           else list(dict.fromkeys(temas_notificacao)))
        return {"generos": deepcopy(cliente["generos"]),
                "temas_notificacao": deepcopy(cliente["temas_notificacao"])}

    @atomico
    def registrar_compra(self, cliente_id, livro_id, pontos, expira_em=None, avisar_em=None):
        livro = self._livro(livro_id)
        inteiro_nao_negativo(pontos, "Pontos")
        expiracao = self._data(expira_em) if expira_em is not None else None
        aviso = self._data(avisar_em) if avisar_em is not None else None
        if aviso and (not expiracao or aviso >= expiracao):
            raise ErroLivraria("O aviso deve ocorrer antes da expiração dos pontos.")
        compra = {"id": uuid4().hex, "livro": deepcopy(livro), "pontos": pontos,
                  "data": self.agora().isoformat(),
                  "expira_em": expiracao.isoformat() if expiracao else None,
                  "avisar_em": aviso.isoformat() if aviso else None, "_avisado": False}
        self._cliente(cliente_id)["compras"].append(compra)
        return {k: deepcopy(v) for k, v in compra.items() if not k.startswith("_")}

    @atomico
    def historico(self, cliente_id):
        return [{k: deepcopy(v) for k, v in compra.items() if not k.startswith("_")}
                for compra in self._cliente(cliente_id)["compras"]]

    @atomico
    def fidelidade(self, cliente_id):
        cliente = self._cliente(cliente_id)
        saldo = sum(c["pontos"] for c in cliente["compras"]
                    if c["expira_em"] is None or self._data(c["expira_em"]) > self.agora())
        return {"saldo": saldo, "cartao": {"cliente_id": cliente_id, "numero": f"LIV-{cliente_id}"},
                "cupons": deepcopy(cliente["cupons"])}

    @atomico
    def conceder_cupom(self, cliente_id, codigo, termos):
        cupom = {"codigo": texto_obrigatorio(codigo, "o código do cupom"),
                 "termos": texto_obrigatorio(termos, "os termos do cupom")}
        self._cliente(cliente_id)["cupons"].append(cupom)
        self._notificar(cliente_id, "fidelidade", f'Você recebeu o cupom {cupom["codigo"]}.')
        return deepcopy(cupom)

    @atomico
    def recomendacoes(self, cliente_id):
        cliente = self._cliente(cliente_id)
        comprados = {c["livro"]["id"] for c in cliente["compras"]}
        generos = {g.casefold() for g in cliente["generos"]}
        generos.update(c["livro"]["genero"].casefold() for c in cliente["compras"])
        return [deepcopy(l) for l in self.repositorio.todos()
                if l["genero"].casefold() in generos and l["id"] not in comprados]

    @atomico
    def adicionar_desejo(self, cliente_id, livro_id):
        livro = self._livro(livro_id)
        desejos = self._cliente(cliente_id)["desejos"]
        if livro_id not in desejos:
            desejos.append(livro_id)
        return deepcopy(livro)

    @atomico
    def desejos(self, cliente_id):
        return [self.livro(i) for i in self._cliente(cliente_id)["desejos"]]

    @atomico
    def entrar_fila(self, cliente_id):
        self._cliente(cliente_id)
        if cliente_id not in self.dados.fila():
            self.dados.fila().append(cliente_id)
        return {"posicao": self.dados.fila().index(cliente_id) + 1}

    @atomico
    def oferecer_horario(self, livreiro, quando):
        nome = texto_obrigatorio(livreiro, "o livreiro")
        data = self._data(quando, futuro=True)
        horario = {"id": uuid4().hex, "livreiro": nome, "quando": data.isoformat(), "cliente_id": None}
        self.dados.salvar("horarios", horario["id"], horario)
        return deepcopy(horario)

    @atomico
    def agendar(self, cliente_id, horario_id):
        horario = self._recurso("horarios", horario_id, "Horário")
        self._data(horario["quando"], futuro=True)
        if horario["cliente_id"] not in (None, cliente_id):
            raise ErroLivraria("Este horário já foi agendado.", 409)
        self._cliente(cliente_id)
        horario["cliente_id"] = cliente_id
        return deepcopy(horario)

    @atomico
    def configurar_loja(self, horario, lotacao):
        horario = texto_obrigatorio(horario, "o horário de funcionamento")
        inteiro_nao_negativo(lotacao, "Lotação")
        self.dados.configurar_loja(horario, lotacao)

    @atomico
    def informacoes_loja(self):
        return self.dados.informacoes_loja()

    @atomico
    def cadastrar_evento(self, titulo, quando, local, capacidade=None, lembrar_em=None):
        titulo = texto_obrigatorio(titulo, "o título do evento")
        local = texto_obrigatorio(local, "o local do evento")
        data = self._data(quando, futuro=True)
        if capacidade is not None:
            inteiro_nao_negativo(capacidade, "Capacidade")
        lembrete = self._data(lembrar_em) if lembrar_em is not None else None
        if lembrete and lembrete >= data:
            raise ErroLivraria("O lembrete deve ocorrer antes do evento.")
        evento = {"id": uuid4().hex, "titulo": titulo, "quando": data.isoformat(), "local": local,
                  "capacidade": capacidade, "lembrar_em": lembrete.isoformat() if lembrete else None,
                  "inscritos": set(), "avisados": set()}
        self.dados.salvar("eventos", evento["id"], evento)
        return next(e for e in self.eventos() if e["id"] == evento["id"])

    @atomico
    def eventos(self, cliente_id=None):
        return [{k: deepcopy(v) for k, v in e.items() if k not in {"inscritos", "avisados"}}
                | {"inscrito": cliente_id in e["inscritos"],
                   "vagas": None if e["capacidade"] is None else e["capacidade"] - len(e["inscritos"])}
                for e in sorted(self.dados.listar("eventos"), key=lambda e: self._data(e["quando"]))]

    @atomico
    def inscrever(self, cliente_id, evento_id):
        evento = self._recurso("eventos", evento_id, "Evento")
        self._data(evento["quando"], futuro=True)
        if cliente_id not in evento["inscritos"]:
            if evento["capacidade"] is not None and len(evento["inscritos"]) >= evento["capacidade"]:
                raise ErroLivraria("Não há vagas disponíveis neste evento.", 409)
            self._cliente(cliente_id)
            evento["inscritos"].add(cliente_id)
        return {"evento_id": evento_id, "confirmada": True}

    @atomico
    def criar_clube(self, nome):
        nome = texto_obrigatorio(nome, "o nome do clube")
        clube = {"id": uuid4().hex, "nome": nome, "membros": set(), "opinioes": []}
        self.dados.salvar("clubes", clube["id"], clube)
        return {"id": clube["id"], "nome": nome}

    @atomico
    def participar_clube(self, cliente_id, clube_id):
        clube = self._recurso("clubes", clube_id, "Clube")
        self._cliente(cliente_id)
        clube["membros"].add(cliente_id)
        return {"clube_id": clube_id, "participando": True}

    @atomico
    def publicar_opiniao(self, cliente_id, clube_id, texto):
        clube = self._recurso("clubes", clube_id, "Clube")
        texto = texto_obrigatorio(texto, "sua opinião")
        if cliente_id not in clube["membros"]:
            raise ErroLivraria("Participe do clube antes de publicar.", 409)
        opiniao = {"cliente": cliente_id, "texto": texto}
        clube["opinioes"].append(opiniao)
        return deepcopy(opiniao)

    @atomico
    def clubes(self, cliente_id):
        return [{"id": c["id"], "nome": c["nome"], "participando": cliente_id in c["membros"],
                 "membros": len(c["membros"]), "opinioes": deepcopy(c["opinioes"])}
                for c in self.dados.listar("clubes")]

    @atomico
    def processar_lembretes(self):
        agora = self.agora()
        for cliente in self.dados.listar("clientes"):
            for compra in cliente["compras"]:
                if (compra["avisar_em"] and not compra["_avisado"]
                    and self._data(compra["avisar_em"]) <= agora < self._data(compra["expira_em"])):
                    self._notificar(cliente["id"], "fidelidade",
                                    f'{compra["pontos"]} pontos expiram em {compra["expira_em"]}.')
                    compra["_avisado"] = True
        for evento in self.dados.listar("eventos"):
            if (evento["lembrar_em"]
                and self._data(evento["lembrar_em"]) <= agora < self._data(evento["quando"])):
                for cliente_id in evento["inscritos"] - evento["avisados"]:
                    self._notificar(cliente_id, "eventos",
                                    f'Lembrete: {evento["titulo"]} em {evento["quando"]}.')
                    evento["avisados"].add(cliente_id)

    @atomico
    def estado(self, cliente_id):
        cliente = self._cliente(cliente_id)
        self.processar_lembretes()
        return {
            "cliente": {k: deepcopy(cliente[k]) for k in ("id", "generos", "temas_notificacao")},
            "livros": self.buscar(), "reservas": self.reservas(cliente_id),
            "fidelidade": self.fidelidade(cliente_id), "loja": self.informacoes_loja(),
            "fila": {"posicao": self.dados.fila().index(cliente_id) + 1 if cliente_id in self.dados.fila() else None},
            "horarios": [{k: v for k, v in h.items() if k != "cliente_id"}
                         for h in self.dados.listar("horarios")
                         if h["cliente_id"] is None and self._data(h["quando"]) > self.agora()],
            "agendamentos": [deepcopy(h) for h in self.dados.listar("horarios") if h["cliente_id"] == cliente_id],
            "eventos": self.eventos(cliente_id), "clubes": self.clubes(cliente_id),
            "desejos": self.desejos(cliente_id), "historico": self.historico(cliente_id),
            "recomendacoes": self.recomendacoes(cliente_id), "notificacoes": self.notificacoes(cliente_id),
        }

    @atomico
    def publicar_avaliacao(self, cliente_id, livro_id, nota, texto):
        self._livro(livro_id)
        conteudo = Avaliacao(nota, texto)
        texto_obrigatorio(cliente_id, "o identificador do cliente")
        if self.dados.obter_avaliacao(livro_id, cliente_id) is not None:
            raise ErroLivraria("Você já publicou uma avaliação deste livro.", 409)
        self._cliente(cliente_id)
        avaliacao = {
            "id": uuid4().hex, "cliente": f"Leitor {uuid4().hex[:8]}",
            "nota": conteudo.nota, "texto": conteudo.texto,
            "data": self.agora().isoformat(),
        }
        self.dados.salvar_avaliacao(livro_id, cliente_id, avaliacao)
        return deepcopy(avaliacao)
