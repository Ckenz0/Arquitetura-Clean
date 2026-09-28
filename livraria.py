"""Domínio da aplicação, conforme docs/specs/livraria.md."""

from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
from threading import RLock
from uuid import uuid4

NAO_INFORMADO = object()
TEMAS = {"estoque", "reservas", "fidelidade", "eventos"}


def inteiro_nao_negativo(valor, campo):
    if type(valor) is not int or valor < 0:
        raise ErroLivraria(f"{campo} deve ser um inteiro não negativo.")
    return valor


def texto_obrigatorio(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise ErroLivraria(f"Informe {campo}.")
    return valor.strip()


class ErroLivraria(ValueError):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


def filtrar_livros(livros, **criterios):
    """Contrato de filtragem exata utilizado no laboratório de TDD."""
    return [deepcopy(livro) for livro in livros
            if all(livro.get(campo) == valor for campo, valor in criterios.items())]


class RepositorioLivros:
    def __init__(self, livros=None):
        self._livros = deepcopy(livros or [])

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


class Catalogo:
    """Fachada do repositório usada nos exemplos de BDD."""

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
    def __init__(self, livros=None, agora=None):
        super().__init__(RepositorioLivros(livros))
        self.agora = agora or (lambda: datetime.now(timezone.utc))
        self._lock = RLock()
        self._clientes = {}
        self._reservas = {}
        self._acompanhamentos = {}
        self._fila = []
        self._horarios = {}
        self._eventos = {}
        self._clubes = {}
        self._loja = {"horario": "Não informado", "lotacao": 0}

    def _cliente(self, cliente_id):
        texto_obrigatorio(cliente_id, "o identificador do cliente")
        if cliente_id not in self._clientes:
            self._clientes[cliente_id] = {
                "id": cliente_id, "generos": [], "temas_notificacao": None,
                "desejos": [], "compras": [], "cupons": [], "notificacoes": [],
            }
        return self._clientes[cliente_id]

    def _data(self, valor, futuro=False):
        try:
            data = datetime.fromisoformat(texto_obrigatorio(valor, "uma data ISO válida"))
            if data.tzinfo is None:
                data = data.astimezone()
        except (ValueError, TypeError, OSError, OverflowError):
            raise ErroLivraria("Informe uma data e hora válidas.") from None
        if futuro and data <= self.agora():
            raise ErroLivraria("A data deve estar no futuro.")
        return data

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
            return colecao[identificador]
        except (KeyError, TypeError):
            raise ErroLivraria(f"{nome} não encontrado.", 404) from None

    def _reserva(self, reserva_id, cliente_id=None):
        reserva = self._recurso(self._reservas, reserva_id, "Reserva")
        if cliente_id is not None and reserva["cliente_id"] != cliente_id:
            raise ErroLivraria("Reserva não encontrada.", 404)
        return reserva

    def _livro(self, livro_id):
        for livro in self.repositorio._livros:
            if livro["id"] == livro_id:
                return livro
        raise ErroLivraria("Livro não encontrado.", 404)

    @atomico
    def livro(self, livro_id):
        return deepcopy(self._livro(livro_id))

    @atomico
    def por_codigo(self, codigo):
        for livro in self.repositorio._livros:
            if livro.get("codigo") == codigo:
                return deepcopy(livro)
        raise ErroLivraria("Código de barras não encontrado.", 404)

    @atomico
    def buscar(self, q="", genero="", lancamentos=False):
        termo = q.strip().casefold()
        return [deepcopy(livro) for livro in self.repositorio._livros
                if (not termo or termo in livro["titulo"].casefold()
                    or termo in livro["autor"].casefold())
                and (not genero or genero.casefold() == livro["genero"].casefold())
                and (not lancamentos or livro.get("lancamento"))]

    @atomico
    def reservar(self, cliente_id, livro_id, prazo, embrulho=False):
        livro = self._livro(livro_id)
        data = self._data(prazo, futuro=True)
        if type(embrulho) is not bool:
            raise ErroLivraria("Embrulho deve ser verdadeiro ou falso.")
        if livro["estoque"] <= 0:
            raise ErroLivraria("Livro sem exemplares disponíveis.", 409)
        self._cliente(cliente_id)
        reserva = {
            "id": uuid4().hex, "cliente_id": cliente_id,
            "livro_id": livro_id, "titulo": livro["titulo"],
            "prazo": data.isoformat(), "embrulho": embrulho, "status": "pendente",
        }
        livro["estoque"] -= 1
        self._reservas[reserva["id"]] = reserva
        return deepcopy(reserva)

    @atomico
    def reservas(self, cliente_id):
        return [deepcopy(r) for r in self._reservas.values() if r["cliente_id"] == cliente_id]

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
        self._acompanhamentos.setdefault(livro_id, set()).add(cliente_id)
        return {"livro_id": livro_id, "acompanhando": True}

    @atomico
    def atualizar_estoque(self, livro_id, quantidade):
        inteiro_nao_negativo(quantidade, "Estoque")
        livro = self._livro(livro_id)
        anterior = livro["estoque"]
        livro["estoque"] = quantidade
        if anterior == 0 and quantidade > 0:
            for cliente_id in self._acompanhamentos.get(livro_id, set()):
                self._notificar(cliente_id, "estoque", f'{livro["titulo"]} voltou ao estoque.')
        return deepcopy(livro)

    @atomico
    def notificacoes(self, cliente_id):
        return deepcopy(self._cliente(cliente_id)["notificacoes"])

    @atomico
    def preferencias(self, cliente_id, generos=NAO_INFORMADO,
                     temas_notificacao=NAO_INFORMADO):
        for valor, campo in [(generos, "Gêneros"), (temas_notificacao, "Temas")]:
            if valor is NAO_INFORMADO or (campo == "Temas" and valor is None):
                continue
            if not isinstance(valor, list) or any(not isinstance(v, str) or not v.strip() for v in valor):
                raise ErroLivraria(f"{campo} deve ser uma lista de textos.")
        if temas_notificacao is not NAO_INFORMADO and temas_notificacao is not None:
            if not set(temas_notificacao).issubset(TEMAS):
                raise ErroLivraria("Tema de notificação inválido.")
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
        return [deepcopy(l) for l in self.repositorio._livros
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
        if cliente_id not in self._fila:
            self._fila.append(cliente_id)
        return {"posicao": self._fila.index(cliente_id) + 1}

    @atomico
    def oferecer_horario(self, livreiro, quando):
        nome = texto_obrigatorio(livreiro, "o livreiro")
        data = self._data(quando, futuro=True)
        horario = {"id": uuid4().hex, "livreiro": nome, "quando": data.isoformat(), "cliente_id": None}
        self._horarios[horario["id"]] = horario
        return deepcopy(horario)

    @atomico
    def agendar(self, cliente_id, horario_id):
        horario = self._recurso(self._horarios, horario_id, "Horário")
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
        self._loja = {"horario": horario, "lotacao": lotacao}

    @atomico
    def informacoes_loja(self):
        return deepcopy(self._loja)

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
        self._eventos[evento["id"]] = evento
        return next(e for e in self.eventos() if e["id"] == evento["id"])

    @atomico
    def eventos(self, cliente_id=None):
        return [{k: deepcopy(v) for k, v in e.items() if k not in {"inscritos", "avisados"}}
                | {"inscrito": cliente_id in e["inscritos"],
                   "vagas": None if e["capacidade"] is None else e["capacidade"] - len(e["inscritos"])}
                for e in sorted(self._eventos.values(), key=lambda e: self._data(e["quando"]))]

    @atomico
    def inscrever(self, cliente_id, evento_id):
        evento = self._recurso(self._eventos, evento_id, "Evento")
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
        self._clubes[clube["id"]] = clube
        return {"id": clube["id"], "nome": nome}

    @atomico
    def participar_clube(self, cliente_id, clube_id):
        clube = self._recurso(self._clubes, clube_id, "Clube")
        self._cliente(cliente_id)
        clube["membros"].add(cliente_id)
        return {"clube_id": clube_id, "participando": True}

    @atomico
    def publicar_opiniao(self, cliente_id, clube_id, texto):
        clube = self._recurso(self._clubes, clube_id, "Clube")
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
                for c in self._clubes.values()]

    @atomico
    def processar_lembretes(self):
        agora = self.agora()
        for cliente in self._clientes.values():
            for compra in cliente["compras"]:
                if (compra["avisar_em"] and not compra["_avisado"]
                    and self._data(compra["avisar_em"]) <= agora < self._data(compra["expira_em"])):
                    self._notificar(cliente["id"], "fidelidade",
                                    f'{compra["pontos"]} pontos expiram em {compra["expira_em"]}.')
                    compra["_avisado"] = True
        for evento in self._eventos.values():
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
            "fila": {"posicao": self._fila.index(cliente_id) + 1 if cliente_id in self._fila else None},
            "horarios": [{k: v for k, v in h.items() if k != "cliente_id"}
                         for h in self._horarios.values()
                         if h["cliente_id"] is None and self._data(h["quando"]) > self.agora()],
            "agendamentos": [deepcopy(h) for h in self._horarios.values() if h["cliente_id"] == cliente_id],
            "eventos": self.eventos(cliente_id), "clubes": self.clubes(cliente_id),
            "desejos": self.desejos(cliente_id), "historico": self.historico(cliente_id),
            "recomendacoes": self.recomendacoes(cliente_id), "notificacoes": self.notificacoes(cliente_id),
        }
