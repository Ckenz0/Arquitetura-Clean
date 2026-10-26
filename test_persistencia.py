"""Persistência real em TXT, reinício, consistência e recuperação de falhas."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from importlib import import_module
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app import create_app
from livraria import ErroLivraria, Livraria


AGORA = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def persistente(arquivo):
    return import_module("infrastructure.composition").criar_persistente(
        arquivo, agora=lambda: AGORA,
    )


def test_txt_preserva_estado_completo_e_tipos_apos_recriar_servico(tmp_path):
    arquivo = tmp_path / "livraria.txt"
    loja = persistente(arquivo)
    loja.preferencias("ana", generos=["Fantasia"], temas_notificacao=None)
    loja.adicionar_desejo("ana", "hobbit")
    loja.acompanhar_estoque("ana", "esgotado")
    loja.atualizar_estoque("esgotado", 2)
    reserva = loja.reservar("ana", "1984", (AGORA + timedelta(days=2)).isoformat(), True)
    loja.marcar_pronta(reserva["id"])
    loja.entrar_fila("ana")
    estado = loja.estado("ana")
    loja.agendar("ana", estado["horarios"][0]["id"])
    loja.inscrever("ana", estado["eventos"][0]["id"])
    clube = estado["clubes"][0]["id"]
    loja.participar_clube("ana", clube)
    loja.publicar_opiniao("ana", clube, "Lemos juntas.")
    loja.registrar_compra("ana", "hobbit", 50,
        expira_em=(AGORA + timedelta(days=3)).isoformat(),
        avisar_em=(AGORA + timedelta(days=2)).isoformat())
    loja.conceder_cupom("ana", "LEITURA", "Condições na loja.")
    loja.publicar_avaliacao("ana", "1984", 5, "Ótima leitura.")
    editada = loja.editar_avaliacao("ana", "1984", 4, "Revisei minha opinião.")
    loja.agora = lambda: AGORA + timedelta(days=2, hours=12)
    antes = loja.estado("ana")
    texto = arquivo.read_text(encoding="utf-8")
    assert "Revisei minha opinião." in texto
    assert json.loads(texto)["versao"] == 1
    recarregada = persistente(arquivo)
    recarregada.agora = loja.agora
    assert recarregada.estado("ana") == antes
    assert recarregada.livro("1984", "ana")["minha_avaliacao"] == editada
    recarregada.cancelar_reserva("ana", reserva["id"])
    assert recarregada.livro("1984")["estoque"] == 3
    assert persistente(arquivo).livro("1984")["estoque"] == 3
    quantidade_avisos = len(recarregada.notificacoes("ana"))
    recarregada.atualizar_estoque("esgotado", 0)
    recarregada.atualizar_estoque("esgotado", 1)
    assert len(recarregada.notificacoes("ana")) == quantidade_avisos + 1


@pytest.mark.parametrize("backend", ["memoria", "txt"])
def test_mesmo_caso_de_uso_edita_com_os_dois_adaptadores(tmp_path, backend):
    loja = persistente(tmp_path / "loja.txt") if backend == "txt" else Livraria([
        {"id": "1984", "titulo": "1984", "autor": "Orwell", "genero": "Distopia", "estoque": 3},
    ], agora=lambda: AGORA)
    original = loja.publicar_avaliacao("ana", "1984", 5, "Primeira.")
    editada = loja.editar_avaliacao("ana", "1984", 2, "Revisada.")
    assert editada["id"] == original["id"]
    assert loja.livro("1984", "ana")["minha_avaliacao"]["nota"] == 2


@pytest.mark.parametrize("operacao", ["reserva", "edicao"])
def test_falha_de_gravacao_preserva_txt_e_restaura_memoria(tmp_path, monkeypatch, operacao):
    arquivo = tmp_path / "livraria.txt"
    loja = persistente(arquivo)
    loja.publicar_avaliacao("ana", "1984", 5, "Original.")
    antes = loja.transacao.snapshot()
    bytes_antes = arquivo.read_bytes()
    def falhar(*args, **kwargs):
        raise OSError("disco indisponível")
    monkeypatch.setattr(import_module("infrastructure.txt").os, "replace", falhar)
    with pytest.raises(ErroLivraria) as erro:
        if operacao == "reserva":
            loja.reservar("ana", "1984", (AGORA + timedelta(days=2)).isoformat())
        else:
            loja.editar_avaliacao("ana", "1984", 1, "Nova.")
    assert erro.value.status == 503
    assert str(tmp_path) not in str(erro.value)
    assert loja.transacao.snapshot() == antes
    assert arquivo.read_bytes() == bytes_antes
    assert list(tmp_path.iterdir()) == [arquivo]


@pytest.mark.parametrize("conteudo", ["", "{", "[]", '{"versao":999}',
    '{"versao":true,"livros":[],"estado":{}}', '{"versao":1,"livros":[],"estado":{}}'])
def test_txt_invalido_nao_e_sobrescrito(tmp_path, conteudo):
    arquivo = tmp_path / "livraria.txt"
    arquivo.write_text(conteudo, encoding="utf-8")
    with pytest.raises(ErroLivraria):
        persistente(arquivo)
    assert arquivo.read_text(encoding="utf-8") == conteudo


def test_corrupcao_depois_de_carregar_nao_e_sobrescrita(tmp_path):
    arquivo = tmp_path / "livraria.txt"
    loja = persistente(arquivo)
    arquivo.write_text("dados danificados", encoding="utf-8")
    with pytest.raises(ErroLivraria):
        loja.publicar_avaliacao("ana", "1984", 5, "Não salvar.")
    assert arquivo.read_text(encoding="utf-8") == "dados danificados"


def test_consultas_sem_alteracao_nao_exigem_gravar(tmp_path, monkeypatch):
    arquivo = tmp_path / "livraria.txt"
    loja = persistente(arquivo)
    def falhar(*args, **kwargs):
        raise OSError("gravação desnecessária")
    monkeypatch.setattr(import_module("infrastructure.txt").os, "replace", falhar)
    assert loja.livro("1984")["estoque"] == 3
    assert len(loja.buscar()) == 5


def test_instancias_no_mesmo_processo_leem_as_alteracoes_mais_recentes(tmp_path):
    arquivo = tmp_path / "livraria.txt"
    a, b = persistente(arquivo), persistente(arquivo)
    original = a.publicar_avaliacao("ana", "1984", 5, "Ana.")
    b.publicar_avaliacao("bia", "1984", 4, "Bia.")
    a.editar_avaliacao("ana", "1984", 3, "Ana revisou.")
    livro = b.livro("1984", "ana")
    assert livro["minha_avaliacao"]["id"] == original["id"]
    assert [av["nota"] for av in livro["avaliacoes"] if "nota" in av] == [3, 4]


def test_consultas_do_catalogo_tambem_recarregam_estado_mais_recente(tmp_path):
    arquivo = tmp_path / "livraria.txt"
    a, b = persistente(arquivo), persistente(arquivo)
    a.atualizar_estoque("1984", 1)
    assert b.consultar_estoque("1984") == 1
    assert b.buscar_por_titulo("1984")[0]["estoque"] == 1
    assert b.buscar_por_autor("George Orwell")[0]["estoque"] == 1
    assert b.filtrar_por_genero("Distopia")[0]["estoque"] == 1


def test_instancias_concorrentes_preservam_as_duas_publicacoes(tmp_path):
    arquivo = tmp_path / "livraria.txt"
    a, b = persistente(arquivo), persistente(arquivo)
    def publicar(par):
        loja, cliente = par
        return loja.publicar_avaliacao(cliente, "1984", 5, cliente)
    with ThreadPoolExecutor(max_workers=2) as executor:
        publicadas = list(executor.map(publicar, [(a, "ana"), (b, "bia")]))
    assert len(publicadas) == 2
    assert len(persistente(arquivo).livro("1984")["avaliacoes"]) == 3


def test_reinicio_da_aplicacao_preserva_cookie_dados_e_autoria(tmp_path):
    arquivo = tmp_path / "livraria.txt"
    primeira = create_app(arquivo_dados=arquivo)
    cliente = primeira.test_client()
    cliente.get("/api/estado")
    cliente.post("/api/desejos", json={"livro_id": "hobbit"})
    publicada = cliente.post("/api/livros/1984/avaliacoes", json={"nota": 5, "texto": "Gostei."}).json
    estado = cliente.get("/api/estado").json
    nome_cookie = primeira.config["SESSION_COOKIE_NAME"]
    cookie = cliente.get_cookie(nome_cookie)
    segunda = create_app(arquivo_dados=arquivo)
    outro = segunda.test_client()
    outro.set_cookie(nome_cookie, cookie.value)
    assert outro.get("/api/estado").json == estado
    assert outro.get("/api/livros/1984").json["minha_avaliacao"]["id"] == publicada["id"]
    resposta = outro.patch("/api/livros/1984/avaliacoes/minha", json={"nota": 4, "texto": "Editei após reiniciar."})
    assert resposta.status_code == 200
    assert persistente(arquivo).livro("1984", estado["cliente"]["id"])["minha_avaliacao"]["texto"] == "Editei após reiniciar."


def test_outro_processo_recupera_a_avaliacao_editada_do_txt(tmp_path):
    arquivo = tmp_path / "livraria.txt"
    loja = persistente(arquivo)
    loja.publicar_avaliacao("ana", "1984", 5, "Original.")
    editada = loja.editar_avaliacao("ana", "1984", 2, "Revista em outro momento.")
    codigo = (
        "import sys,json; from infrastructure.composition import criar_persistente; "
        "loja=criar_persistente(sys.argv[1]); "
        "print(json.dumps(loja.livro('1984','ana')['minha_avaliacao']))"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo, str(arquivo)],
        cwd=Path(__file__).parent, check=True, capture_output=True, text=True)
    assert json.loads(resultado.stdout) == editada


def test_importar_modulo_app_nao_cria_dados_de_execucao(tmp_path):
    arquivo = tmp_path / "nao-criar.txt"
    ambiente = dict(os.environ, LIVRARIA_ARQUIVO_DADOS=str(arquivo))
    subprocess.run([sys.executable, "-c", "import app"], cwd=Path(__file__).parent, env=ambiente, check=True)
    assert not arquivo.exists()
    assert not list(tmp_path.iterdir())


def test_http_nao_confirma_edicao_quando_o_disco_falha(tmp_path, monkeypatch):
    arquivo = tmp_path / "livraria.txt"
    cliente = create_app(arquivo_dados=arquivo).test_client()
    original = cliente.post("/api/livros/1984/avaliacoes", json={"nota": 5, "texto": "Original."}).json
    antes = arquivo.read_bytes()
    def falhar(*args, **kwargs):
        raise OSError("disco indisponível")
    with monkeypatch.context() as contexto:
        contexto.setattr(import_module("infrastructure.txt").os, "replace", falhar)
        resposta = cliente.patch("/api/livros/1984/avaliacoes/minha", json={"nota": 1, "texto": "Não gravar."})
    assert resposta.status_code == 503 and resposta.is_json
    assert str(tmp_path) not in resposta.json["erro"]
    assert arquivo.read_bytes() == antes
    assert cliente.get("/api/livros/1984").json["minha_avaliacao"] == original


def test_primeira_sessao_so_e_confirmada_apos_gravar_dados_demo(tmp_path, monkeypatch):
    arquivo = tmp_path / "livraria.txt"
    app = create_app(arquivo_dados=arquivo)
    cliente = app.test_client()
    antes = arquivo.read_bytes()
    def falhar(*args, **kwargs):
        raise OSError("disco indisponível")
    with monkeypatch.context() as contexto:
        contexto.setattr(import_module("infrastructure.txt").os, "replace", falhar)
        resposta = cliente.get("/api/estado")
    assert resposta.status_code == 503
    assert arquivo.read_bytes() == antes
    with cliente.session_transaction() as sessao:
        assert "cliente_id" not in sessao
    estado = cliente.get("/api/estado").json
    assert len(estado["historico"]) == 1
    assert len(estado["fidelidade"]["cupons"]) == 1


@pytest.mark.parametrize("ausente,valor", [(True, None), (False, None), (False, 123), (False, "")])
def test_snapshot_de_compra_com_livro_invalido_e_recusado_sem_sobrescrever(tmp_path, ausente, valor):
    arquivo = tmp_path / "livraria.txt"
    loja = persistente(arquivo)
    loja.registrar_compra("ana", "1984", 20)
    documento = json.loads(arquivo.read_text(encoding="utf-8"))
    livro = documento["estado"]["colecoes"]["clientes"]["ana"]["compras"][0]["livro"]
    if ausente:
        del livro["genero"]
    else:
        livro["genero"] = valor
    arquivo.write_text(json.dumps(documento, ensure_ascii=False), encoding="utf-8")
    bytes_invalidos = arquivo.read_bytes()
    with pytest.raises(ErroLivraria) as erro:
        persistente(arquivo)
    assert erro.value.status == 503
    assert arquivo.read_bytes() == bytes_invalidos
    with pytest.raises(ErroLivraria) as erro:
        loja.preferencias("bia", generos=["Fantasia"])
    assert erro.value.status == 503
    assert arquivo.read_bytes() == bytes_invalidos
