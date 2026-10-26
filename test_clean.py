"""Edição, autoria e fronteiras do núcleo independente da livraria."""

import ast
from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
import subprocess
import sys

import pytest

from app import create_app
from livraria import ErroLivraria, Livraria


AGORA = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
LIVROS = [{"id": "1984", "titulo": "1984", "autor": "George Orwell",
           "genero": "Distopia", "estoque": 3, "codigo": "123",
           "avaliacoes": [{"cliente": "Marina", "texto": "Boa leitura."}]}]


def nova_loja():
    return Livraria(LIVROS, agora=lambda: AGORA)


def test_editar_preserva_identidade_autoria_data_e_quantidade():
    loja = nova_loja()
    original = loja.publicar_avaliacao("ana", "1984", 5, "Gostei.")
    loja.agora = lambda: AGORA + timedelta(hours=1)
    editada = loja.editar_avaliacao("ana", "1984", 3, "  Mudei de opinião.  ")
    for campo in ("id", "cliente", "data"):
        assert editada[campo] == original[campo]
    assert editada["nota"] == 3
    assert editada["texto"] == "Mudei de opinião."
    assert editada["atualizada_em"] == (AGORA + timedelta(hours=1)).isoformat()
    livro = loja.livro("1984", "ana")
    assert len(livro["avaliacoes"]) == 2
    assert livro["minha_avaliacao"] == editada
    assert loja.livro("1984", "bia")["minha_avaliacao"] is None
    assert loja.livro("1984", "bia")["avaliacoes"][-1] == editada
    editada["texto"] = "mutação externa"
    assert loja.livro("1984", "ana")["minha_avaliacao"]["texto"] == "Mudei de opinião."
    with pytest.raises(ErroLivraria) as erro:
        loja.publicar_avaliacao("ana", "1984", 4, "Outra.")
    assert erro.value.status == 409


@pytest.mark.parametrize("nota,texto", [(0, "texto"), (6, "texto"), (True, "texto"),
    (2.5, "texto"), ("4", "texto"), (None, "texto"), (4, " "), (4, None), (4, 123)])
def test_edicao_invalida_preserva_avaliacao(nota, texto):
    loja = nova_loja()
    original = loja.publicar_avaliacao("ana", "1984", 5, "Gostei.")
    with pytest.raises(ErroLivraria) as erro:
        loja.editar_avaliacao("ana", "1984", nota, texto)
    assert erro.value.status == 400
    assert loja.livro("1984", "ana")["minha_avaliacao"] == original


def test_outro_cliente_nao_edita_avaliacao_alheia_nem_a_ilustrativa():
    loja = nova_loja()
    original = loja.publicar_avaliacao("ana", "1984", 5, "Gostei.")
    for cliente, livro in [("bia", "1984"), ("Marina", "1984"), ("ana", "inexistente")]:
        with pytest.raises(ErroLivraria) as erro:
            loja.editar_avaliacao(cliente, livro, 1, "Tentativa.")
        assert erro.value.status == 404
    assert loja.livro("1984", "ana")["minha_avaliacao"] == original


def test_nucleo_funciona_com_ports_sem_importar_framework_ou_armazenamento():
    ports = import_module("use_cases.ports")
    loja = nova_loja()
    assert isinstance(loja.repositorio, ports.LivrosPort)
    assert isinstance(loja.dados, ports.EstadoPort)
    assert isinstance(loja.transacao, ports.TransacaoPort)
    CasoDeUso = import_module("use_cases.livraria").Livraria
    nucleo = CasoDeUso(loja.repositorio, loja.dados, loja.transacao, agora=lambda: AGORA)
    nucleo.publicar_avaliacao("ana", "1984", 5, "Gostei.")
    assert nucleo.editar_avaliacao("ana", "1984", 4, "Revisei.")["nota"] == 4
    codigo = "import sys; import use_cases.livraria; assert not any(m in sys.modules for m in ('flask','repositories','infrastructure','interface_adapters'))"
    subprocess.run([sys.executable, "-c", codigo], cwd=Path(__file__).parent, check=True)


def test_dependencias_apontam_para_o_nucleo():
    raiz = Path(__file__).parent
    externos = {"flask", "werkzeug", "infrastructure", "interface_adapters",
                "repositories", "services", "controllers", "app", "pathlib", "json", "threading", "os"}
    for camada in ("entities", "use_cases"):
        arquivos = list((raiz / camada).glob("*.py"))
        assert arquivos, camada
        for arquivo in arquivos:
            for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
                nomes = []
                if isinstance(no, ast.Import):
                    nomes = [a.name for a in no.names]
                elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
                    nomes = [no.module]
                assert not {n.split('.')[0] for n in nomes} & externos, arquivo
                if camada == "entities":
                    assert not any(n.startswith("use_cases") for n in nomes), arquivo


def test_http_edita_apenas_avaliacao_da_sessao_e_retorna_resultado():
    app = create_app(nova_loja())
    ana, bia = app.test_client(), app.test_client()
    publicada = ana.post("/api/livros/1984/avaliacoes", json={"nota": 5, "texto": "Gostei."}).json
    url = "/api/livros/1984/avaliacoes/minha"
    assert bia.patch(url, json={"nota": 1, "texto": "Outra pessoa."}).status_code == 404
    resposta = ana.patch(url, json={"nota": 4, "texto": "Minha revisão."})
    assert resposta.status_code == 200
    assert resposta.json["id"] == publicada["id"]
    assert resposta.json["texto"] == "Minha revisão."
    assert ana.get("/api/livros/1984").json["minha_avaliacao"] == resposta.json
    livro_bia = bia.get("/api/livros/1984").json
    assert livro_bia["minha_avaliacao"] is None
    assert livro_bia["avaliacoes"][-1] == resposta.json


@pytest.mark.parametrize("corpo", [{}, {"nota": 4}, {"texto": "texto"},
    {"nota": 5, "texto": " "}, {"nota": True, "texto": "texto"},
    {"nota": 4, "texto": "texto", "cliente_id": "outra"}, []])
def test_http_recusa_edicao_invalida_ou_autoria_forjada(corpo):
    cliente = create_app(nova_loja()).test_client()
    original = cliente.post("/api/livros/1984/avaliacoes", json={"nota": 5, "texto": "Original."}).json
    resposta = cliente.patch("/api/livros/1984/avaliacoes/minha", json=corpo)
    assert resposta.status_code == 400 and resposta.is_json
    assert cliente.get("/api/livros/1984").json["minha_avaliacao"] == original
