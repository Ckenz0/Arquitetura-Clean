"""Edição real no navegador, inclusive após reiniciar a aplicação com TXT."""

from contextlib import contextmanager
import os
from pathlib import Path
from threading import Thread

import pytest
from werkzeug.serving import make_server

from app import create_app


@contextmanager
def servidor_txt(arquivo):
    servidor = make_server("127.0.0.1", 0, create_app(arquivo_dados=arquivo))
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{servidor.server_port}"
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=5)


@pytest.mark.interface
@pytest.mark.parametrize("largura,altura", [(1366, 900), (390, 844)])
def test_edicao_cancelamento_erro_e_reinicio_no_navegador(tmp_path, largura, altura):
    navegador = pytest.importorskip("playwright.sync_api")
    executavel = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or next((p for p in [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ] if Path(p).is_file()), None)
    if not executavel:
        pytest.skip("Informe PLAYWRIGHT_BROWSER_EXECUTABLE para executar o teste de interface.")
    arquivo = tmp_path / "livraria.txt"
    with navegador.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executavel, headless=True)
        try:
            contexto = browser.new_context(viewport={"width": largura, "height": altura}, locale="pt-BR")
            page = contexto.new_page()
            page.set_default_timeout(5000)
            erros = []
            page.on("pageerror", lambda erro: erros.append(str(erro)))
            with servidor_txt(arquivo) as url:
                page.goto(url)
                page.locator('.book-card [data-action="detalhes"][data-id="1984"]').click()
                page.get_by_label("Sua nota").select_option("5")
                page.get_by_label("Seu comentário").fill("Minha leitura original.")
                page.get_by_role("button", name="Publicar avaliação", exact=True).click()
                navegador.expect(page.locator("#avaliacao-confirmacao")).to_be_visible()
                original = page.request.get(f"{url}/api/livros/1984").json()["minha_avaliacao"]
                page.get_by_role("button", name="Editar avaliação", exact=True).click()
                navegador.expect(page.get_by_label("Sua nota")).to_have_value("5")
                navegador.expect(page.get_by_label("Seu comentário")).to_have_value("Minha leitura original.")
                page.get_by_label("Sua nota").select_option("4")
                page.get_by_label("Seu comentário").fill("Rascunho cancelado.")
                page.get_by_role("button", name="Cancelar edição", exact=True).click()
                assert page.request.get(f"{url}/api/livros/1984").json()["minha_avaliacao"] == original
                page.get_by_role("button", name="Editar avaliação", exact=True).click()
                page.get_by_label("Sua nota").select_option("2")
                comentario = '<script>window.edicaoInjetada=true</script> Revi minha leitura.'
                page.get_by_label("Seu comentário").fill(comentario)
                capturas = Path(__file__).parent / ".superpowers/screenshots"
                capturas.mkdir(parents=True, exist_ok=True)
                page.locator("#edicao-avaliacao-form").scroll_into_view_if_needed()
                page.screenshot(path=str(capturas / f"edicao-{largura}.png"))
                def falhar(rota):
                    rota.fulfill(status=503, json={"erro": "Não foi possível salvar. Tente novamente."})
                rota_patch = "**/api/livros/1984/avaliacoes/minha"
                page.route(rota_patch, falhar)
                page.get_by_role("button", name="Salvar alterações", exact=True).click()
                navegador.expect(page.locator("#avaliacao-erro")).to_contain_text("Tente novamente")
                navegador.expect(page.get_by_label("Seu comentário")).to_have_value(comentario)
                navegador.expect(page.get_by_label("Sua nota")).to_have_value("2")
                page.unroute(rota_patch, falhar)
                page.route("**/api/livros/1984", falhar)
                page.get_by_role("button", name="Salvar alterações", exact=True).click()
                navegador.expect(page.locator("#avaliacao-confirmacao")).to_contain_text("Alterações salvas")
                navegador.expect(page.locator("#book-reviews")).to_contain_text("Nota 2 de 5")
                navegador.expect(page.locator("#book-reviews .opinion")).to_have_count(2)
                navegador.expect(page.locator("#book-reviews")).to_contain_text(comentario)
                assert page.evaluate("window.edicaoInjetada") is None
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert page.locator("#book-dialog").evaluate("el => el.scrollWidth <= el.clientWidth")
                page.unroute("**/api/livros/1984", falhar)
                outro = browser.new_context()
                outra = outro.new_page()
                outra.goto(url)
                outra.locator('.book-card [data-action="detalhes"][data-id="1984"]').click()
                navegador.expect(outra.locator("#book-reviews")).to_contain_text(comentario)
                assert outra.get_by_role("button", name="Editar avaliação", exact=True).count() == 0
                outro.close()
            with servidor_txt(arquivo) as novo_url:
                page.goto(novo_url)
                page.locator('.book-card [data-action="detalhes"][data-id="1984"]').click()
                navegador.expect(page.get_by_role("button", name="Editar avaliação", exact=True)).to_be_visible()
                editada = page.request.get(f"{novo_url}/api/livros/1984").json()["minha_avaliacao"]
                assert editada["id"] == original["id"]
                assert editada["nota"] == 2 and editada["texto"] == comentario
                assert erros == []
        finally:
            browser.close()
