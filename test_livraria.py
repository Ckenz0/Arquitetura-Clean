"""TDD do domínio, BDD da especificação e integração real com Flask."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import pytest
from pytest_bdd import given, when, then, parsers, scenarios


AGORA = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
PRAZO = "2026-09-29T18:00:00+00:00"
LIVROS = [
    {"id": "1984", "titulo": "1984", "autor": "George Orwell", "ano": 1949,
     "genero": "Distopia", "estoque": 3, "lancamento": False,
     "codigo": "9788535914849", "sinopse": "Uma sociedade sob vigilância.",
     "preco": 49.90, "secao": "Literatura", "prateleira": "A1",
     "avaliacoes": [{"cliente": "Marina", "texto": "Uma leitura marcante."}]},
    {"id": "bichos", "titulo": "A Revolução dos Bichos", "autor": "George Orwell",
     "ano": 1945, "genero": "Distopia", "estoque": 2, "lancamento": False},
    {"id": "hobbit", "titulo": "O Hobbit", "autor": "J.R.R. Tolkien",
     "ano": 1937, "genero": "Fantasia", "estoque": 5, "lancamento": False},
    {"id": "reino", "titulo": "O Novo Reino", "autor": "Ana Silva",
     "ano": 2026, "genero": "Fantasia", "estoque": 4, "lancamento": True},
    {"id": "esgotado", "titulo": "Livro Esgotado", "autor": "Autor Exemplo",
     "genero": "Romance", "estoque": 0, "lancamento": False},
]


def nova_livraria(agora=None):
    return import_module("livraria").Livraria(
        deepcopy(LIVROS), agora=agora or (lambda: AGORA)
    )


@pytest.mark.parametrize("criterios,titulos", [
    ({"autor": "George Orwell"}, ["1984", "A Revolução dos Bichos"]),
    ({"ano": 1949}, ["1984"]),
    ({"genero": "Fantasia"}, ["O Hobbit", "O Novo Reino"]),
    ({"autor": "George Orwell", "genero": "Distopia"},
     ["1984", "A Revolução dos Bichos"]),
    ({"autor": "Autor inexistente"}, []),
])
def test_filtrar_livros_exemplos_tdd(criterios, titulos):
    filtrar = import_module("livraria").filtrar_livros
    assert [l["titulo"] for l in filtrar(LIVROS, **criterios)] == titulos


def test_catalogo_compativel_com_exemplos_bdd():
    modulo = import_module("livraria")
    catalogo = modulo.Catalogo(modulo.RepositorioLivros(deepcopy(LIVROS)))
    assert [l["titulo"] for l in catalogo.buscar_por_titulo("1984")] == ["1984"]
    assert len(catalogo.buscar_por_autor("George Orwell")) == 2
    assert catalogo.buscar_por_titulo("Livro Inexistente") == []
    assert catalogo.consultar_estoque("1984") == 3
    assert catalogo.consultar_estoque("inexistente") == 0
    assert len(catalogo.filtrar_por_genero("Fantasia")) == 2
    assert [l["titulo"] for l in catalogo.listar_lancamentos()] == ["O Novo Reino"]


def test_busca_parcial_sem_diferenciar_caixa():
    loja = nova_livraria()
    assert [l["id"] for l in loja.buscar_por_autor("ORWELL")] == ["1984", "bichos"]
    assert [l["id"] for l in loja.buscar_por_titulo("hob")] == ["hobbit"]
    assert [l["id"] for l in loja.buscar(q="orwell", genero="distopia")] == ["1984", "bichos"]
    assert [l["id"] for l in loja.buscar(lancamentos=True)] == ["reino"]
    assert len(loja.buscar()) == 5


def test_detalhes_codigo_localizacao_e_avaliacoes():
    loja = nova_livraria()
    livro = loja.por_codigo("9788535914849")
    assert livro["id"] == "1984"
    assert livro["preco"] == 49.9
    assert livro["sinopse"] == "Uma sociedade sob vigilância."
    assert (livro["secao"], livro["prateleira"]) == ("Literatura", "A1")
    assert livro["avaliacoes"][0]["texto"] == "Uma leitura marcante."


def test_copias_do_catalogo_nao_permitem_alterar_estoque():
    loja = nova_livraria()
    loja.livro("1984")["estoque"] = -1
    loja.buscar()[0]["estoque"] = -2
    assert loja.consultar_estoque("1984") == 3


def test_codigo_inexistente_produz_erro_do_dominio():
    loja = nova_livraria()
    with pytest.raises(import_module("livraria").ErroLivraria) as erro:
        loja.por_codigo("inexistente")
    assert erro.value.status == 404


def test_reservar_separa_exemplar_e_preserva_prazo_e_presente():
    loja = nova_livraria()
    reserva = loja.reservar("ana", "1984", PRAZO, embrulho=True)
    assert reserva["status"] == "pendente"
    assert reserva["prazo"] == PRAZO
    assert reserva["embrulho"] is True
    assert loja.livro("1984")["estoque"] == 2
    assert loja.reservas("outra") == []


def test_cancelar_duas_vezes_nao_cria_exemplares():
    loja = nova_livraria()
    reserva = loja.reservar("ana", "1984", PRAZO)
    assert loja.cancelar_reserva("ana", reserva["id"])["status"] == "cancelada"
    loja.cancelar_reserva("ana", reserva["id"])
    assert loja.livro("1984")["estoque"] == 3


@pytest.mark.parametrize("prazo", ["ontem", "2026-09-26T18:00:00+00:00", "", None])
def test_prazo_invalido_nao_altera_estoque(prazo):
    loja = nova_livraria()
    with pytest.raises(ValueError):
        loja.reservar("ana", "1984", prazo)
    assert loja.livro("1984")["estoque"] == 3
    assert loja.reservas("ana") == []


def test_estoque_zero_recusa_reserva():
    loja = nova_livraria()
    with pytest.raises(ValueError):
        loja.reservar("ana", "esgotado", PRAZO)
    assert loja.livro("esgotado")["estoque"] == 0


def test_duas_clientes_disputando_ultimo_exemplar():
    from concurrent.futures import ThreadPoolExecutor
    loja = nova_livraria()
    loja.atualizar_estoque("1984", 1)

    def reservar(cliente):
        try:
            loja.reservar(cliente, "1984", PRAZO)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(reservar, ["ana", "bia"])) == [False, True]
    assert loja.livro("1984")["estoque"] == 0


def test_outro_cliente_nao_pode_alterar_reserva():
    loja = nova_livraria()
    reserva = loja.reservar("ana", "1984", PRAZO)
    with pytest.raises(ValueError):
        loja.cancelar_reserva("bia", reserva["id"])
    with pytest.raises(ValueError):
        loja.alterar_prazo("bia", reserva["id"], PRAZO)
    assert loja.reservas("ana")[0]["status"] == "pendente"


def test_alterar_prazo_e_reserva_pronta_notifica_uma_vez():
    loja = nova_livraria()
    reserva = loja.reservar("ana", "1984", PRAZO)
    novo = "2026-10-05T18:00:00+00:00"
    assert loja.alterar_prazo("ana", reserva["id"], novo)["prazo"] == novo
    assert loja.marcar_pronta(reserva["id"])["status"] == "pronta"
    loja.marcar_pronta(reserva["id"])
    assert [n["tema"] for n in loja.notificacoes("ana")] == ["reservas"]


def test_cancelada_nao_pode_ficar_pronta_ou_mudar_prazo():
    loja = nova_livraria()
    reserva = loja.reservar("ana", "1984", PRAZO)
    loja.cancelar_reserva("ana", reserva["id"])
    with pytest.raises(ValueError):
        loja.marcar_pronta(reserva["id"])
    with pytest.raises(ValueError):
        loja.alterar_prazo("ana", reserva["id"], PRAZO)


def test_reposicao_notifica_assinante_uma_vez_por_reposicao():
    loja = nova_livraria()
    loja.acompanhar_estoque("ana", "esgotado")
    loja.acompanhar_estoque("ana", "esgotado")
    loja.atualizar_estoque("esgotado", 2)
    loja.atualizar_estoque("esgotado", 3)
    assert [n["tema"] for n in loja.notificacoes("ana")] == ["estoque"]
    assert loja.notificacoes("bia") == []


@pytest.mark.parametrize("quantidade", [-1, True, "2", 2.5])
def test_quantidade_invalida_nao_altera_estoque(quantidade):
    loja = nova_livraria()
    with pytest.raises(ValueError):
        loja.atualizar_estoque("1984", quantidade)
    assert loja.livro("1984")["estoque"] == 3


def test_preferencias_de_notificacao_todos_nenhum_e_tema():
    loja = nova_livraria()
    for cliente, temas in [("ana", []), ("bia", ["eventos"]), ("clara", None)]:
        loja.preferencias(cliente, temas_notificacao=temas)
        loja.acompanhar_estoque(cliente, "esgotado")
    loja.atualizar_estoque("esgotado", 2)
    assert loja.notificacoes("ana") == []
    assert loja.notificacoes("bia") == []
    assert len(loja.notificacoes("clara")) == 1


@pytest.mark.parametrize("dados", [
    {"generos": "Fantasia"}, {"generos": [1]},
    {"temas_notificacao": ["qualquer"]}, {"temas_notificacao": "eventos"},
])
def test_preferencias_invalidas_nao_modificam_estado(dados):
    loja = nova_livraria()
    loja.preferencias("ana", generos=["Fantasia"])
    with pytest.raises(ValueError):
        loja.preferencias("ana", **dados)
    assert loja.estado("ana")["cliente"]["generos"] == ["Fantasia"]


def test_compras_creditam_pontos_recebidos_e_historico_isolado():
    loja = nova_livraria()
    loja.registrar_compra("ana", "1984", 20)
    loja.registrar_compra("ana", "hobbit", 15)
    assert loja.fidelidade("ana")["saldo"] == 35
    assert loja.fidelidade("ana")["cartao"]["cliente_id"] == "ana"
    assert [c["livro"]["id"] for c in loja.historico("ana")] == ["1984", "hobbit"]
    assert loja.historico("bia") == []
    assert loja.fidelidade("bia")["saldo"] == 0


@pytest.mark.parametrize("pontos", [-1, True, "20", 1.5])
def test_credito_invalido_nao_registra_compra(pontos):
    loja = nova_livraria()
    with pytest.raises(ValueError):
        loja.registrar_compra("ana", "1984", pontos)
    assert loja.historico("ana") == []


def test_validade_de_pontos_no_limite_e_aviso_sem_duplicar():
    relogio = [AGORA]
    loja = nova_livraria(agora=lambda: relogio[0])
    loja.registrar_compra("ana", "1984", 20,
                          expira_em="2026-09-30T12:00:00+00:00",
                          avisar_em="2026-09-27T12:00:00+00:00")
    loja.processar_lembretes()
    loja.processar_lembretes()
    assert [n["tema"] for n in loja.notificacoes("ana")] == ["fidelidade"]
    assert loja.fidelidade("ana")["saldo"] == 20
    relogio[0] = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
    assert loja.fidelidade("ana")["saldo"] == 0


def test_cupons_exibem_termos_fornecidos():
    loja = nova_livraria()
    loja.conceder_cupom("ana", "LEITURA", "Desconto informado no caixa")
    cupom = loja.fidelidade("ana")["cupons"][0]
    assert cupom == {"codigo": "LEITURA", "termos": "Desconto informado no caixa"}


def test_recomendacoes_por_historico_e_preferencias_sem_comprados():
    loja = nova_livraria()
    assert loja.recomendacoes("ana") == []
    loja.registrar_compra("ana", "1984", 20)
    assert [l["id"] for l in loja.recomendacoes("ana")] == ["bichos"]
    loja.preferencias("ana", generos=["Fantasia"])
    assert [l["id"] for l in loja.recomendacoes("ana")] == ["bichos", "hobbit", "reino"]


def test_lista_de_desejos_nao_duplica_e_isola_clientes():
    loja = nova_livraria()
    loja.adicionar_desejo("ana", "hobbit")
    loja.adicionar_desejo("ana", "hobbit")
    assert [l["id"] for l in loja.desejos("ana")] == ["hobbit"]
    assert loja.desejos("bia") == []


def test_fila_preserva_ordem_e_nao_duplica():
    loja = nova_livraria()
    assert loja.entrar_fila("ana")["posicao"] == 1
    assert loja.entrar_fila("bia")["posicao"] == 2
    assert loja.entrar_fila("ana")["posicao"] == 1


def test_horario_agendado_nao_pode_ser_ocupado_por_outra_cliente():
    loja = nova_livraria()
    horario = loja.oferecer_horario("Carlos", "2026-09-28T14:00:00+00:00")
    assert loja.agendar("ana", horario["id"])["livreiro"] == "Carlos"
    with pytest.raises(ValueError):
        loja.agendar("bia", horario["id"])
    assert loja.estado("bia")["agendamentos"] == []


def test_info_loja_exibe_valores_informados():
    loja = nova_livraria()
    loja.configurar_loja("Seg–Sáb, 09h às 19h", 12)
    assert loja.informacoes_loja() == {"horario": "Seg–Sáb, 09h às 19h", "lotacao": 12}


def criar_evento(loja, capacidade=1):
    return loja.cadastrar_evento("Conversa com autores", "2026-09-28T18:00:00+00:00",
                                 "Salão da loja", capacidade=capacidade,
                                 lembrar_em="2026-09-27T12:00:00+00:00")


def test_inscricao_garante_vaga_sem_duplicacao():
    loja = nova_livraria()
    evento = criar_evento(loja)
    loja.inscrever("ana", evento["id"])
    loja.inscrever("ana", evento["id"])
    with pytest.raises(ValueError):
        loja.inscrever("bia", evento["id"])
    assert loja.eventos("ana")[0]["vagas"] == 0
    assert loja.eventos("ana")[0]["inscrito"] is True
    assert loja.eventos("bia")[0]["inscrito"] is False


def test_evento_sem_capacidade_nao_inventa_limite():
    loja = nova_livraria()
    evento = criar_evento(loja, capacidade=None)
    for cliente in ["ana", "bia"]:
        loja.inscrever(cliente, evento["id"])
    assert loja.eventos("ana")[0]["vagas"] is None


def test_cadastrar_eventos_fora_de_ordem_devolve_evento_criado():
    loja = nova_livraria()
    distante = loja.cadastrar_evento("Encontro distante", "2026-10-10T18:00:00+00:00", "Loja")
    proximo = loja.cadastrar_evento("Encontro próximo", "2026-10-01T18:00:00+00:00", "Loja")
    assert proximo["titulo"] == "Encontro próximo"
    assert proximo["id"] != distante["id"]
    assert [e["id"] for e in loja.eventos()] == [proximo["id"], distante["id"]]


def test_lembrete_apenas_para_inscritos_e_antes_do_evento():
    relogio = [AGORA - timedelta(seconds=1)]
    loja = nova_livraria(agora=lambda: relogio[0])
    evento = criar_evento(loja)
    loja.inscrever("ana", evento["id"])
    loja.processar_lembretes()
    assert loja.notificacoes("ana") == []
    relogio[0] = AGORA
    loja.processar_lembretes()
    loja.processar_lembretes()
    assert [n["tema"] for n in loja.notificacoes("ana")] == ["eventos"]
    assert loja.notificacoes("bia") == []


def test_clube_participacao_e_opiniao_identificada():
    loja = nova_livraria()
    clube = loja.criar_clube("Leituras compartilhadas")
    with pytest.raises(ValueError):
        loja.publicar_opiniao("ana", clube["id"], "Ainda não participo")
    loja.participar_clube("ana", clube["id"])
    loja.publicar_opiniao("ana", clube["id"], "Gostei muito.")
    assert loja.clubes("ana")[0]["opinioes"] == [{"cliente": "ana", "texto": "Gostei muito."}]
    assert loja.clubes("bia")[0]["participando"] is False
    with pytest.raises(ValueError):
        loja.publicar_opiniao("ana", clube["id"], "  ")


# O arquivo .feature é derivado da fonte única de verdade e vive apenas no
# diretório temporário do sistema. Não há segunda especificação no projeto.
_temporario_bdd = TemporaryDirectory(prefix="livraria-bdd-")
_spec = (Path(__file__).parent / "docs/specs/livraria.md").read_text(encoding="utf-8")
_gherkin = re.search(r"```gherkin\s*\n(.*?)```", _spec, re.DOTALL).group(1)
_feature = Path(_temporario_bdd.name) / "livraria.feature"
_feature.write_text(_gherkin, encoding="utf-8")
scenarios(str(_feature))


@given("que existem livros cadastrados no catálogo", target_fixture="contexto")
def livros_cadastrados():
    loja = nova_livraria()
    loja.configurar_loja("Seg–Sáb, 09h às 19h", 12)
    return {"loja": loja}


@given(parsers.parse('que sou a cliente "{cliente}"'))
def cliente_bdd(contexto, cliente):
    contexto["cliente"] = cliente


def id_por_titulo(contexto, titulo):
    return contexto["loja"].buscar_por_titulo(titulo)[0]["id"]


@when(parsers.parse('eu buscar pelo título "{titulo}"'))
def buscar_titulo(contexto, titulo):
    contexto["resultado"] = contexto["loja"].buscar_por_titulo(titulo)


@when(parsers.parse('eu buscar pelo autor "{autor}"'))
def buscar_autor(contexto, autor):
    contexto["resultado"] = contexto["loja"].buscar_por_autor(autor)


@then(parsers.parse('o livro "{titulo}" deve ser retornado'))
def contem_livro(contexto, titulo):
    assert titulo in [l["titulo"] for l in contexto["resultado"]]


@then(parsers.parse('o livro "{titulo}" não deve ser retornado'))
def nao_contem_livro(contexto, titulo):
    assert titulo not in [l["titulo"] for l in contexto["resultado"]]


@then(parsers.parse("devem ser retornados {quantidade:d} livros"))
@then(parsers.parse("deve ser retornado {quantidade:d} lançamento"))
def quantidade_livros(contexto, quantidade):
    assert len(contexto["resultado"]) == quantidade


@then("nenhum livro deve ser retornado")
def nenhum_livro(contexto):
    assert contexto["resultado"] == []


@when(parsers.parse('eu consultar a disponibilidade do livro "{titulo}"'))
def disponibilidade(contexto, titulo):
    contexto["resultado"] = contexto["loja"].consultar_estoque(titulo)


@then(parsers.parse("devem ser informados {quantidade:d} exemplares disponíveis"))
def quantidade_estoque(contexto, quantidade):
    assert contexto["resultado"] == quantidade


@when(parsers.parse('eu filtrar os livros pelo gênero "{genero}"'))
def filtro_genero(contexto, genero):
    contexto["resultado"] = contexto["loja"].filtrar_por_genero(genero)


@then(parsers.parse('devem ser retornados apenas livros do gênero "{genero}"'))
def apenas_genero(contexto, genero):
    assert contexto["resultado"]
    assert all(l["genero"] == genero for l in contexto["resultado"])


@when("eu consultar os lançamentos da semana")
def lancamentos(contexto):
    contexto["resultado"] = contexto["loja"].listar_lancamentos()


@given(parsers.parse('que acompanho a reposição de "{titulo}"'))
def acompanhar(contexto, titulo):
    contexto["loja"].acompanhar_estoque(contexto["cliente"], id_por_titulo(contexto, titulo))


@when(parsers.parse('a loja repuser {quantidade:d} exemplares de "{titulo}"'))
def repor(contexto, quantidade, titulo):
    contexto["loja"].atualizar_estoque(id_por_titulo(contexto, titulo), quantidade)


@then(parsers.parse('devo receber uma notificação do tema "{tema}"'))
def recebeu_notificacao(contexto, tema):
    assert tema in [n["tema"] for n in contexto["loja"].notificacoes(contexto["cliente"])]


@given(parsers.parse('que comprei "{titulo}" e recebi {pontos:d} pontos'))
@when(parsers.parse('a loja registrar minha compra de "{titulo}" com {pontos:d} pontos'))
def compra(contexto, titulo, pontos):
    contexto["loja"].registrar_compra(contexto["cliente"], id_por_titulo(contexto, titulo), pontos)


@when("eu consultar minhas recomendações")
def recomendar(contexto):
    contexto["resultado"] = contexto["loja"].recomendacoes(contexto["cliente"])


@when(parsers.parse('eu consultar os detalhes de "{titulo}"'))
def detalhes(contexto, titulo):
    contexto["resultado"] = contexto["loja"].livro(id_por_titulo(contexto, titulo))


@when(parsers.parse('eu consultar o código de barras "{codigo}"'))
def codigo_barras(contexto, codigo):
    contexto["resultado"] = contexto["loja"].por_codigo(codigo)


@then(parsers.parse('devo ver a avaliação "{texto}"'))
def avaliacao(contexto, texto):
    assert texto in [a["texto"] for a in contexto["resultado"]["avaliacoes"]]


@then(parsers.parse('devo ver a seção "{secao}" e a prateleira "{prateleira}"'))
def localizacao(contexto, secao, prateleira):
    assert (contexto["resultado"]["secao"], contexto["resultado"]["prateleira"]) == (secao, prateleira)


@then(parsers.parse('devo ver a sinopse "{texto}"'))
def sinopse(contexto, texto):
    assert contexto["resultado"]["sinopse"] == texto


@then(parsers.parse("devo ver o preço de {preco:f} reais"))
def preco(contexto, preco):
    assert contexto["resultado"]["preco"] == preco


@when("eu entrar na fila virtual")
def fila(contexto):
    contexto["resultado"] = contexto["loja"].entrar_fila(contexto["cliente"])


@then(parsers.parse("minha posição na fila deve ser {posicao:d}"))
def posicao_fila(contexto, posicao):
    assert contexto["resultado"]["posicao"] == posicao


@given(parsers.parse('que há um horário do livreiro "{livreiro}" em "{quando}"'))
def horario_bdd(contexto, livreiro, quando):
    contexto["horario"] = contexto["loja"].oferecer_horario(livreiro, quando)


@when("eu agendar esse atendimento")
def agendamento(contexto):
    contexto["resultado"] = contexto["loja"].agendar(contexto["cliente"], contexto["horario"]["id"])


@then(parsers.parse('meu atendimento deve estar confirmado com "{livreiro}"'))
def agendamento_confirmado(contexto, livreiro):
    assert contexto["resultado"]["livreiro"] == livreiro
    assert contexto["resultado"]["cliente_id"] == contexto["cliente"]


@when("eu consultar as informações da loja")
def info_loja(contexto):
    contexto["resultado"] = contexto["loja"].informacoes_loja()


@then(parsers.parse('devo ver o horário "{horario}"'))
def horario_loja(contexto, horario):
    assert contexto["resultado"]["horario"] == horario


@then(parsers.parse("devo ver a lotação atual de {pessoas:d} pessoas"))
def lotacao(contexto, pessoas):
    assert contexto["resultado"]["lotacao"] == pessoas


@given(parsers.parse('que reservei "{titulo}" até "{prazo}"'))
@when(parsers.parse('eu reservar "{titulo}" até "{prazo}"'))
def reservar_bdd(contexto, titulo, prazo):
    contexto["reserva"] = contexto["loja"].reservar(contexto["cliente"], id_por_titulo(contexto, titulo), prazo)


@when(parsers.parse('eu reservar "{titulo}" como presente até "{prazo}"'))
def reservar_presente(contexto, titulo, prazo):
    contexto["reserva"] = contexto["loja"].reservar(
        contexto["cliente"], id_por_titulo(contexto, titulo), prazo, embrulho=True)


@then(parsers.parse('minha reserva deve estar "{status}"'))
def status_reserva(contexto, status):
    assert contexto["reserva"]["status"] == status


@then(parsers.parse('devem restar {quantidade:d} exemplares de "{titulo}"'))
def exemplares_restantes(contexto, quantidade, titulo):
    assert contexto["loja"].consultar_estoque(titulo) == quantidade


@when(parsers.parse('eu tentar reservar "{titulo}"'))
def tentar_reserva(contexto, titulo):
    with pytest.raises(import_module("livraria").ErroLivraria) as erro:
        contexto["loja"].reservar(contexto["cliente"], id_por_titulo(contexto, titulo), PRAZO)
    contexto["erro"] = erro.value


@then("a operação deve ser recusada")
def operacao_recusada(contexto):
    assert contexto["erro"].status == 409


@when(parsers.parse('eu alterar o prazo para "{prazo}"'))
def alterar_prazo_bdd(contexto, prazo):
    contexto["reserva"] = contexto["loja"].alterar_prazo(contexto["cliente"], contexto["reserva"]["id"], prazo)


@then(parsers.parse('minha reserva deve ter prazo "{prazo}"'))
def prazo_reserva(contexto, prazo):
    assert contexto["reserva"]["prazo"] == prazo


@when("a loja marcar minha reserva como pronta")
def reserva_pronta(contexto):
    contexto["reserva"] = contexto["loja"].marcar_pronta(contexto["reserva"]["id"])


@when("eu cancelar minha reserva")
def cancelar_bdd(contexto):
    contexto["reserva"] = contexto["loja"].cancelar_reserva(contexto["cliente"], contexto["reserva"]["id"])


@when("eu consultar minha fidelidade")
def fidelidade_bdd(contexto):
    contexto["resultado"] = contexto["loja"].fidelidade(contexto["cliente"])


@then(parsers.parse("meu saldo de pontos deve ser {pontos:d}"))
def saldo(contexto, pontos):
    assert contexto["loja"].fidelidade(contexto["cliente"])["saldo"] == pontos


@when(parsers.parse('a loja conceder o cupom "{codigo}" com os termos "{termos}"'))
def cupom_bdd(contexto, codigo, termos):
    contexto["loja"].conceder_cupom(contexto["cliente"], codigo, termos)


@then(parsers.parse('devo ver o cupom "{codigo}"'))
def recebeu_cupom(contexto, codigo):
    assert codigo in [c["codigo"] for c in contexto["loja"].fidelidade(contexto["cliente"])["cupons"]]


@then(parsers.parse('meu cartão digital deve identificar "{cliente}"'))
def cartao(contexto, cliente):
    assert contexto["resultado"]["cartao"]["cliente_id"] == cliente


@given(parsers.parse('que tenho {pontos:d} pontos válidos até "{expira}" com aviso em "{aviso}"'))
def pontos_com_aviso(contexto, pontos, expira, aviso):
    contexto["loja"].registrar_compra(contexto["cliente"], "1984", pontos, expira_em=expira, avisar_em=aviso)


@when("o aplicativo processar os lembretes")
def lembretes(contexto):
    contexto["loja"].processar_lembretes()


@given(parsers.parse('que há um evento chamado "{titulo}"'))
def evento_bdd(contexto, titulo):
    contexto["evento"] = contexto["loja"].cadastrar_evento(
        titulo, "2026-09-28T18:00:00+00:00", "Salão da loja", capacidade=10,
        lembrar_em="2026-09-27T12:00:00+00:00")


@when("eu consultar a agenda de eventos")
def agenda(contexto):
    contexto["resultado"] = contexto["loja"].eventos(contexto["cliente"])


@then(parsers.parse('devo ver o evento "{titulo}"'))
def evento_na_agenda(contexto, titulo):
    assert titulo in [e["titulo"] for e in contexto["resultado"]]


@given("que estou inscrita nesse evento")
@when("eu me inscrever nesse evento")
def inscricao(contexto):
    contexto["inscricao"] = contexto["loja"].inscrever(contexto["cliente"], contexto["evento"]["id"])


@then("minha inscrição deve estar confirmada")
def inscricao_confirmada(contexto):
    assert contexto["inscricao"]["confirmada"] is True


@given(parsers.parse('que há um clube chamado "{nome}"'))
def clube_bdd(contexto, nome):
    contexto["clube"] = contexto["loja"].criar_clube(nome)


@when(parsers.parse('eu participar desse clube e publicar "{texto}"'))
def participar_e_opinar(contexto, texto):
    contexto["loja"].participar_clube(contexto["cliente"], contexto["clube"]["id"])
    contexto["loja"].publicar_opiniao(contexto["cliente"], contexto["clube"]["id"], texto)


@then(parsers.parse('o clube deve exibir minha opinião "{texto}"'))
def opiniao_no_clube(contexto, texto):
    assert {"cliente": contexto["cliente"], "texto": texto} in contexto["loja"].clubes(contexto["cliente"])[0]["opinioes"]


@when(parsers.parse('eu adicionar "{titulo}" à lista de desejos'))
def desejo_bdd(contexto, titulo):
    contexto["loja"].adicionar_desejo(contexto["cliente"], id_por_titulo(contexto, titulo))


@then(parsers.parse('minha lista de desejos deve conter "{titulo}"'))
def desejo_na_lista(contexto, titulo):
    assert titulo in [l["titulo"] for l in contexto["loja"].desejos(contexto["cliente"])]


@when("eu consultar meu histórico de compras")
def historico_bdd(contexto):
    contexto["resultado"] = contexto["loja"].historico(contexto["cliente"])


@then(parsers.parse('meu histórico deve conter "{titulo}"'))
def livro_no_historico(contexto, titulo):
    assert titulo in [c["livro"]["titulo"] for c in contexto["resultado"]]


@when(parsers.parse('eu escolher o gênero preferido "{genero}"'))
def preferencia_genero(contexto, genero):
    contexto["loja"].preferencias(contexto["cliente"], generos=[genero])


@then(parsers.parse('minhas recomendações devem incluir "{titulo}"'))
def recomendacao_preferencia(contexto, titulo):
    assert titulo in [l["titulo"] for l in contexto["loja"].recomendacoes(contexto["cliente"])]


@given(parsers.parse('que aceito apenas notificações de "{tema}"'))
def preferencia_tema(contexto, tema):
    contexto["loja"].preferencias(contexto["cliente"], temas_notificacao=[tema])


@then("não devo receber notificações")
def sem_notificacoes(contexto):
    assert contexto["loja"].notificacoes(contexto["cliente"]) == []


@then("minha reserva deve ter embrulho especial")
def embrulho_especial(contexto):
    assert contexto["reserva"]["embrulho"] is True


def cliente_http():
    loja = nova_livraria()
    app = import_module("app").create_app(loja)
    app.config.update(TESTING=True, SECRET_KEY="apenas-para-testes")
    return app, app.test_client(), loja


def test_api_busca_filtros_detalhes_e_codigo():
    _, cliente, _ = cliente_http()
    assert [l["id"] for l in cliente.get("/api/livros?q=orwell").json] == ["1984", "bichos"]
    assert [l["id"] for l in cliente.get("/api/livros?genero=Fantasia&lancamentos=1").json] == ["reino"]
    assert cliente.get("/api/livros/1984").json["estoque"] == 3
    assert cliente.get("/api/codigo/9788535914849").json["id"] == "1984"
    assert cliente.get("/api/livros/inexistente").status_code == 404


def test_api_reserva_presente_prazo_cancelamento_e_isolamento():
    app, cliente, _ = cliente_http()
    resposta = cliente.post("/api/reservas", json={"livro_id": "1984", "prazo": PRAZO, "embrulho": True})
    assert resposta.status_code == 201
    reserva = resposta.json
    assert reserva["embrulho"] is True
    outro = app.test_client()
    assert outro.get("/api/estado").json["reservas"] == []
    assert outro.post(f'/api/reservas/{reserva["id"]}/cancelar').status_code == 404
    novo = "2026-10-01T18:00:00+00:00"
    assert cliente.patch(f'/api/reservas/{reserva["id"]}', json={"prazo": novo}).json["prazo"] == novo
    assert cliente.post(f'/api/reservas/{reserva["id"]}/cancelar').json["status"] == "cancelada"
    assert cliente.get("/api/livros/1984").json["estoque"] == 3


@pytest.mark.parametrize("payload", [
    {}, [], "não sou um objeto", None,
    {"livro_id": "1984"},
    {"livro_id": "1984", "prazo": "ontem"},
    {"livro_id": "1984", "prazo": PRAZO, "embrulho": "false"},
    {"livro_id": "1984", "prazo": PRAZO, "embrulho": 1},
])
def test_api_entrada_invalida_nao_modifica_estado(payload):
    _, cliente, _ = cliente_http()
    resposta = cliente.post("/api/reservas", json=payload)
    assert resposta.status_code == 400
    assert isinstance(resposta.json["erro"], str)
    assert cliente.get("/api/livros/1984").json["estoque"] == 3


def test_api_json_malformado_e_conflito_retornam_json():
    _, cliente, _ = cliente_http()
    resposta = cliente.post("/api/reservas", data="{", content_type="application/json")
    assert resposta.status_code == 400
    assert "erro" in resposta.json
    esgotado = cliente.post("/api/reservas", json={"livro_id": "esgotado", "prazo": PRAZO})
    assert esgotado.status_code == 409
    assert "erro" in esgotado.json
    assert cliente.post("/api/estoque", json={"livro_id": "1984", "quantidade": 99}).status_code == 404


@pytest.mark.parametrize("prazo", ["0001-01-01T00:00:00", "9999-12-31T23:59:59"])
def test_api_datas_fora_dos_limites_nao_causam_erro_interno(prazo):
    _, cliente, _ = cliente_http()
    resposta = cliente.post("/api/reservas", json={"livro_id": "1984", "prazo": prazo})
    # A conversão de data sem fuso tem limites diferentes por plataforma;
    # entradas suportadas são válidas, entradas não suportadas são erro 400.
    assert resposta.status_code in {400, 201}
    assert cliente.get("/api/livros/1984").json["estoque"] == (3 if resposta.status_code == 400 else 2)


@pytest.mark.parametrize("acao", ["fila", "cancelar", "inscrever", "clube"])
def test_api_acoes_sem_campos_validam_corpo_fornecido(acao):
    _, cliente, loja = cliente_http()
    cliente_id = cliente.get("/api/estado").json["cliente"]["id"]
    reserva = loja.reservar(cliente_id, "1984", PRAZO)
    evento = criar_evento(loja)
    clube = loja.criar_clube("Leituras compartilhadas")
    caminhos = {"fila": "/api/fila", "cancelar": f'/api/reservas/{reserva["id"]}/cancelar',
                "inscrever": f'/api/eventos/{evento["id"]}/inscricoes',
                "clube": f'/api/clubes/{clube["id"]}/participar'}
    for corpo in ["{", "[]", "null", "{}"]:
        resposta = cliente.post(caminhos[acao], data=corpo, content_type="application/json")
        esperado = (200 if acao == "cancelar" else 201) if corpo == "{}" else 400
        assert resposta.status_code == esperado
        if corpo != "{}":
            estado = loja.estado(cliente_id)
            assert estado["fila"]["posicao"] is None
            assert estado["reservas"][0]["status"] == "pendente"
            assert estado["eventos"][0]["inscrito"] is False
            assert estado["clubes"][0]["participando"] is False


def test_api_desejos_preferencias_e_recomendacoes():
    _, cliente, _ = cliente_http()
    assert cliente.post("/api/desejos", json={"livro_id": "hobbit"}).status_code == 201
    resposta = cliente.patch("/api/preferencias", json={"generos": ["Fantasia"], "temas_notificacao": []})
    assert resposta.status_code == 200
    estado = cliente.get("/api/estado").json
    assert [l["id"] for l in estado["desejos"]] == ["hobbit"]
    assert [l["id"] for l in estado["recomendacoes"]] == ["hobbit", "reino"]
    assert estado["cliente"]["temas_notificacao"] == []
    assert cliente.patch("/api/preferencias", json={"generos": "Fantasia"}).status_code == 400


def test_api_fila_horarios_eventos_clube_e_notificacoes():
    _, cliente, loja = cliente_http()
    horario = loja.oferecer_horario("Carlos", "2026-09-28T14:00:00+00:00")
    evento = criar_evento(loja)
    clube = loja.criar_clube("Leituras compartilhadas")
    assert cliente.post("/api/fila").json["posicao"] == 1
    assert cliente.post("/api/agendamentos", json={"horario_id": horario["id"]}).status_code == 201
    assert cliente.post(f'/api/eventos/{evento["id"]}/inscricoes').status_code == 201
    assert cliente.post(f'/api/clubes/{clube["id"]}/participar').status_code == 201
    opiniao = cliente.post(f'/api/clubes/{clube["id"]}/opinioes', json={"texto": "<script>exemplo</script>"})
    assert opiniao.status_code == 201
    assert opiniao.json["texto"] == "<script>exemplo</script>"
    assert cliente.post("/api/avisos-estoque", json={"livro_id": "esgotado"}).status_code == 201
    loja.atualizar_estoque("esgotado", 3)
    estado = cliente.get("/api/estado").json
    assert {n["tema"] for n in estado["notificacoes"]} == {"estoque", "eventos"}
    assert estado["agendamentos"][0]["livreiro"] == "Carlos"


def test_pagina_inicial_entrega_html():
    _, cliente, _ = cliente_http()
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert resposta.mimetype == "text/html"


def test_pagina_entrega_estilos_e_scripts_referenciados():
    """A View precisa carregar seus assets reais, com os tipos corretos."""
    _, cliente, _ = cliente_http()
    html = cliente.get("/").get_data(as_text=True)
    estilos = re.findall(r'<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"', html)
    scripts = re.findall(r'<script\b[^>]*src="([^"]+)"', html)
    assert estilos, "A página deve referenciar sua folha de estilos."
    assert scripts, "A página deve referenciar seu JavaScript."
    for caminho in estilos + scripts:
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200, caminho
        assert resposta.data, caminho
        tipos = {"text/css"} if caminho in estilos else {
            "text/javascript", "application/javascript",
        }
        assert resposta.mimetype in tipos, caminho


@pytest.mark.interface
def test_interface_fluxos_desktop_e_mobile():
    """Verifica a interface real; instalação de Playwright/Chrome é opcional."""
    import os
    from threading import Thread
    from werkzeug.serving import make_server
    navegador = pytest.importorskip("playwright.sync_api")
    executavel = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE")
    if not executavel:
        executavel = next((p for p in [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        ] if Path(p).is_file()), None)
    if not executavel:
        pytest.skip("Informe PLAYWRIGHT_BROWSER_EXECUTABLE para executar o teste de interface.")
    app = import_module("app").create_app()
    servidor = make_server("127.0.0.1", 0, app)
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        with navegador.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=executavel, headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 900}, locale="pt-BR")
            page.set_default_timeout(8000)
            erros = []
            page.on("pageerror", lambda erro: erros.append(str(erro)))
            page.goto(f"http://127.0.0.1:{servidor.server_port}")
            navegador.expect(page.locator(".book-card")).to_have_count(5)
            page.locator("#busca").fill("ORWELL")
            navegador.expect(page.locator(".book-card")).to_have_count(2)
            page.locator("#busca").fill("inexistente")
            navegador.expect(page.locator(".book-card")).to_have_count(0)
            page.locator("#busca").fill("")
            page.locator("#genero").select_option("Fantasia")
            page.locator("#lancamentos").check()
            navegador.expect(page.locator(".book-card")).to_have_count(1)
            page.locator("#lancamentos").uncheck()
            page.locator("#genero").select_option("")
            page.locator('.book-card [data-action="detalhes"][data-id="1984"]').click()
            navegador.expect(page.locator("#book-dialog")).to_be_visible()
            navegador.expect(page.locator("#book-details")).to_contain_text("A1")
            page.locator("#book-dialog [data-close]").click()
            page.locator('[data-action="escanear"]').click()
            page.locator("#barcode").fill("9788535914849")
            page.locator('#scan-form button[type="submit"]').click()
            navegador.expect(page.locator("#book-dialog")).to_be_visible()
            page.locator("#book-dialog [data-close]").click()
            page.locator('.book-card [data-action="reservar"][data-id="hobbit"]').click()
            page.locator("#reserve-deadline").fill((datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"))
            page.locator("#reserve-gift").check()
            page.locator('#reserve-form button[type="submit"]').click()
            navegador.expect(page.locator("#reserve-dialog")).not_to_be_visible()
            navegador.expect(page.locator("#reservas")).to_contain_text("Presente com embrulho especial")
            page.locator('#reservas [data-action="prazo"]').click()
            page.locator("#new-deadline").fill((datetime.now() + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M"))
            page.locator('#deadline-form button[type="submit"]').click()
            navegador.expect(page.locator("#deadline-dialog")).not_to_be_visible()
            page.locator('#reservas [data-action="cancelar"]').click()
            navegador.expect(page.locator("#reservas .status")).to_have_text("cancelada")
            page.locator("#fila-button").click()
            navegador.expect(page.locator("#fila-posicao")).to_contain_text("posição na fila: 1")
            navegador.expect(page.locator("#fila-button")).to_be_disabled()
            page.locator("#agendamento-horario").select_option(index=1)
            page.locator('#agendamento-form button[type="submit"]').click()
            navegador.expect(page.locator("#agendamentos")).to_contain_text("Agendado para")
            page.locator('nav [data-tab="comunidade"]').click()
            page.locator('#eventos [data-action="inscrever"]').first.click()
            navegador.expect(page.locator('#eventos button').first).to_have_text("Inscrição confirmada ✓")
            page.locator('#clubes [data-action="clube"]').click()
            page.locator('.opiniao-form textarea').fill('<script>window.injecao = true</script>Gostei do livro.')
            page.locator('.opiniao-form button[type="submit"]').click()
            navegador.expect(page.locator('#clubes .opinion')).to_contain_text('Gostei do livro.')
            assert page.evaluate("window.injecao") is None
            page.locator('nav [data-tab="perfil"]').click()
            page.locator('#preferencias-form input[name="generos"][value="Fantasia"]').check()
            page.locator('#preferencias-form input[name="temas"][value="estoque"]').uncheck()
            page.locator('#preferencias-form button[type="submit"]').click()
            navegador.expect(page.locator('#toast')).to_have_text('Suas preferências foram salvas.')
            page.reload()
            page.locator('nav [data-tab="perfil"]').click()
            navegador.expect(page.locator('#preferencias-form input[name="generos"][value="Fantasia"]')).to_be_checked()
            navegador.expect(page.locator('#preferencias-form input[name="temas"][value="estoque"]')).not_to_be_checked()
            page.locator('nav [data-tab="catalogo"]').click()
            page.locator('.book-card [data-action="desejo"][data-id="hobbit"]').click()
            navegador.expect(page.locator('.book-card [data-action="desejo"][data-id="hobbit"]')).to_have_attribute('aria-pressed', 'true')
            page.locator('.book-card [data-action="acompanhar"]').click()
            navegador.expect(page.locator('#toast')).to_contain_text('aviso de reposição')
            page.locator('[data-action="notificacoes"]').click()
            navegador.expect(page.locator('#notificacoes')).to_contain_text('pontos expiram')
            page.locator('#notifications-dialog [data-close]').click()
            page.set_viewport_size({"width":390, "height":844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            navegador.expect(page.locator('.book-card')).to_have_count(5)
            assert erros == []
            browser.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=5)


@pytest.mark.interface
def test_interface_atualizacao_durante_consulta_em_andamento():
    """Uma ação não pode perder sua atualização por existir um GET em voo."""
    import os
    from threading import Thread
    from werkzeug.serving import make_server
    navegador = pytest.importorskip("playwright.sync_api")
    executavel = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or next((p for p in [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ] if Path(p).is_file()), None)
    if not executavel:
        pytest.skip("Informe PLAYWRIGHT_BROWSER_EXECUTABLE para executar o teste de interface.")
    servidor = make_server("127.0.0.1", 0, import_module("app").create_app())
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        with navegador.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=executavel, headless=True)
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{servidor.server_port}")
            navegador.expect(page.locator(".book-card")).to_have_count(5)
            antigo = page.request.get(f"http://127.0.0.1:{servidor.server_port}/api/estado").json()
            capturadas = []
            def capturar_primeira(rota):
                if capturadas:
                    rota.continue_()
                else:
                    capturadas.append(rota)
            page.route("**/api/estado", capturar_primeira)
            with page.expect_request("**/api/estado"):
                page.evaluate("void atualizar()")
            assert page.request.post(f"http://127.0.0.1:{servidor.server_port}/api/desejos", data={"livro_id": "hobbit"}).status == 201
            assert len(capturadas) == 1
            page.evaluate("window.refreshConcluido=false; void atualizar().then(() => {window.refreshConcluido=true})")
            capturadas[0].fulfill(json=antigo)
            page.wait_for_function("window.refreshConcluido")
            navegador.expect(page.locator('.book-card [data-action="desejo"][data-id="hobbit"]')).to_have_attribute("aria-pressed", "true")
            browser.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=5)
