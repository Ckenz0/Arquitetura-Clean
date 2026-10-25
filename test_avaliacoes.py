"""Regras, armazenamento e contrato HTTP da publicação de avaliações."""

import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

import pytest

from app import create_app
from livraria import ErroLivraria, Livraria


def nova_loja():
    return Livraria([
        {"id": "1984", "titulo": "1984", "autor": "George Orwell",
         "genero": "Distopia", "estoque": 3,
         "avaliacoes": [{"cliente": "Marina", "texto": "Uma leitura marcante."}]},
    ], agora=lambda: datetime(2026, 10, 25, 12, tzinfo=timezone.utc))


def test_avaliacao_publicada_e_visivel_sem_expor_autoria_interna():
    loja = nova_loja()
    avaliacao = loja.publicar_avaliacao("sessao-privada-ana", "1984", 5, "  Excelente leitura.  ")
    assert avaliacao["nota"] == 5
    assert avaliacao["texto"] == "Excelente leitura."
    assert avaliacao["cliente"].startswith("Leitor ")
    assert "sessao-privada-ana" not in str(avaliacao)
    livro = loja.livro("1984", "sessao-privada-ana")
    assert livro["avaliacoes"] == [
        {"cliente": "Marina", "texto": "Uma leitura marcante."}, avaliacao,
    ]
    assert livro["ja_avaliou"] is True
    assert loja.livro("1984", "bia")["ja_avaliou"] is False
    livro["avaliacoes"][-1]["texto"] = "alterado fora do serviço"
    assert loja.livro("1984")["avaliacoes"][-1]["texto"] == "Excelente leitura."


@pytest.mark.parametrize("nota", [0, 6, -1, True, False, 3.5, "5", None, [], {}])
def test_nota_invalida_nao_modifica_as_avaliacoes(nota):
    loja = nova_loja()
    antes = loja.livro("1984")
    with pytest.raises(ErroLivraria) as erro:
        loja.publicar_avaliacao("ana", "1984", nota, "Gostei.")
    assert erro.value.status == 400
    assert loja.livro("1984") == antes


@pytest.mark.parametrize("texto", ["", "   ", None, 123, [], {}])
def test_comentario_invalido_nao_modifica_as_avaliacoes(texto):
    loja = nova_loja()
    antes = loja.livro("1984")
    with pytest.raises(ErroLivraria) as erro:
        loja.publicar_avaliacao("ana", "1984", 4, texto)
    assert erro.value.status == 400
    assert loja.livro("1984") == antes


def test_um_cliente_publica_uma_vez_por_livro_mas_outro_pode_publicar():
    loja = nova_loja()
    loja.publicar_avaliacao("ana", "1984", 5, "Primeira opinião.")
    with pytest.raises(ErroLivraria) as erro:
        loja.publicar_avaliacao("ana", "1984", 1, "Segunda opinião.")
    assert erro.value.status == 409
    loja.publicar_avaliacao("bia", "1984", 4, "Outra leitura.")
    assert len(loja.livro("1984")["avaliacoes"]) == 3


def test_publicacoes_concorrentes_nao_duplicam_avaliacao():
    loja = nova_loja()
    def publicar(_):
        try:
            loja.publicar_avaliacao("ana", "1984", 5, "Gostei.")
            return 201
        except ErroLivraria as erro:
            return erro.status
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(publicar, range(2))) == [201, 409]
    assert len(loja.livro("1984")["avaliacoes"]) == 2


def test_servico_utiliza_repositorios_injetados_reais():
    repositorios = import_module("repositories")
    livros = repositorios.RepositorioLivros(nova_loja().buscar())
    dados = repositorios.RepositorioEstado()
    servico = import_module("services").Livraria(repositorio=livros, dados=dados)
    avaliacao = servico.publicar_avaliacao("ana", "1984", 5, "Gostei.")
    assert dados.listar_avaliacoes("1984") == [avaliacao]
    outro_servico = import_module("services").Livraria(repositorio=livros, dados=dados)
    assert outro_servico.livro("1984", "ana")["ja_avaliou"] is True
    assert outro_servico.livro("1984")["avaliacoes"][-1] == avaliacao


def test_dominio_valida_avaliacao_sem_conhecer_http_ou_repositorios():
    Avaliacao = import_module("domain.avaliacao").Avaliacao
    assert Avaliacao(1, "  Não gostei.  ").texto == "Não gostei."
    assert Avaliacao(5, "Gostei.").nota == 5
    with pytest.raises(ErroLivraria):
        Avaliacao(True, "Gostei.")


def test_fronteiras_de_dependencia_das_camadas():
    raiz = Path(__file__).parent
    for camada, proibidos in {
        "domain": {"flask", "controllers", "services", "repositories", "app"},
        "repositories": {"flask", "controllers", "services", "app"},
        "services": {"flask", "controllers", "app"},
        "controllers": {"repositories"},
    }.items():
        arquivos = list((raiz / camada).glob("*.py"))
        assert arquivos, f"Camada ausente: {camada}"
        for arquivo in arquivos:
            for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
                nomes = []
                if isinstance(no, ast.Import):
                    nomes = [alias.name for alias in no.names]
                elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
                    nomes = [no.module]
                assert not {nome.split('.')[0] for nome in nomes} & proibidos, arquivo


def test_http_publica_e_mostra_avaliacao_a_outras_sessoes():
    app = create_app(nova_loja())
    ana, bia = app.test_client(), app.test_client()
    resposta = ana.post("/api/livros/1984/avaliacoes", json={"nota": 5, "texto": "Muito bom!"})
    assert resposta.status_code == 201
    assert resposta.json["nota"] == 5
    assert ana.get("/api/livros/1984").json["ja_avaliou"] is True
    livro_bia = bia.get("/api/livros/1984").json
    assert livro_bia["ja_avaliou"] is False
    assert livro_bia["avaliacoes"][-1] == resposta.json
    with ana.session_transaction() as sessao:
        assert sessao["cliente_id"] not in str(livro_bia["avaliacoes"])
    repetida = ana.post("/api/livros/1984/avaliacoes", json={"nota": 4, "texto": "Repetida."})
    assert repetida.status_code == 409 and repetida.is_json
    assert bia.post("/api/livros/1984/avaliacoes", json={"nota": 1, "texto": "Não gostei."}).status_code == 201


@pytest.mark.parametrize("corpo", [
    {}, {"texto": "Gostei."}, {"nota": 5}, {"nota": 0, "texto": "Gostei."},
    {"nota": True, "texto": "Gostei."}, {"nota": "5", "texto": "Gostei."},
    {"nota": 5, "texto": "   "}, {"nota": 5, "texto": 123},
    {"nota": 5, "texto": "Gostei.", "cliente_id": "outra-pessoa"}, [],
])
def test_http_recusa_entrada_invalida_sem_publicar(corpo):
    cliente = create_app(nova_loja()).test_client()
    resposta = cliente.post("/api/livros/1984/avaliacoes", json=corpo)
    assert resposta.status_code == 400 and resposta.is_json
    assert len(cliente.get("/api/livros/1984").json["avaliacoes"]) == 1


def test_http_erro_de_livro_corpo_e_isolamento_de_aplicacoes():
    a, b = create_app(nova_loja()).test_client(), create_app(nova_loja()).test_client()
    assert a.post("/api/livros/inexistente/avaliacoes", json={"nota": 5, "texto": "Gostei."}).status_code == 404
    assert a.post("/api/livros/1984/avaliacoes", data='{', content_type="application/json").status_code == 400
    assert a.post("/api/livros/1984/avaliacoes", data="texto").status_code == 400
    assert a.post("/api/livros/1984/avaliacoes", json={"nota": 5, "texto": "Gostei."}).status_code == 201
    assert len(b.get("/api/livros/1984").json["avaliacoes"]) == 1
