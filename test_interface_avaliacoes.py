"""Publicação de avaliações pela interface real, em desktop e celular."""

import os
from pathlib import Path
from threading import Thread

import pytest
from werkzeug.serving import make_server

from app import create_app


@pytest.mark.interface
@pytest.mark.parametrize("largura,altura", [(1366, 900), (390, 844)])
def test_interface_publica_avaliacao_e_preserva_rascunho_em_erro(largura, altura):
    navegador = pytest.importorskip("playwright.sync_api")
    executavel = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or next((p for p in [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ] if Path(p).is_file()), None)
    if not executavel:
        pytest.skip("Informe PLAYWRIGHT_BROWSER_EXECUTABLE para executar o teste de interface.")
    servidor = make_server("127.0.0.1", 0, create_app())
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{servidor.server_port}"
    try:
        with navegador.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=executavel, headless=True)
            contexto = browser.new_context(viewport={"width": largura, "height": altura}, locale="pt-BR")
            page = contexto.new_page()
            page.set_default_timeout(5000)
            erros = []
            page.on("pageerror", lambda erro: erros.append(str(erro)))
            page.goto(url)
            page.locator('.book-card [data-action="detalhes"][data-id="1984"]').click()
            formulario = page.locator("#avaliacao-form")
            navegador.expect(formulario).to_be_visible()
            formulario.scroll_into_view_if_needed()
            capturas = Path(__file__).parent / ".superpowers/screenshots"
            capturas.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(capturas / f"avaliacao-form-{largura}.png"))
            page.get_by_label("Sua nota").select_option("5")
            comentario = '<script>window.avaliacaoInjetada=true</script> Leitura excelente.'
            page.get_by_label("Seu comentário").fill(comentario)
            def falhar(rota):
                rota.fulfill(status=503, json={"erro": "Não foi possível publicar. Tente novamente."})
            page.route("**/api/livros/1984/avaliacoes", falhar)
            page.get_by_role("button", name="Publicar avaliação", exact=True).click()
            navegador.expect(page.locator("#avaliacao-erro")).to_contain_text("Tente novamente")
            navegador.expect(page.get_by_label("Seu comentário")).to_have_value(comentario)
            navegador.expect(page.get_by_label("Sua nota")).to_have_value("5")
            page.unroute("**/api/livros/1984/avaliacoes", falhar)
            def falhar_consulta(rota):
                rota.fulfill(status=503, json={"erro": "Consulta indisponível."})
            page.route("**/api/livros/1984", falhar_consulta)
            page.get_by_role("button", name="Publicar avaliação", exact=True).click()
            navegador.expect(page.locator("#avaliacao-confirmacao")).to_contain_text("Você já publicou")
            navegador.expect(page.locator("#book-details")).to_contain_text("Nota 5 de 5")
            navegador.expect(page.locator("#book-details .opinion").last).to_contain_text(comentario)
            assert page.evaluate("window.avaliacaoInjetada") is None
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.locator("#book-dialog").evaluate("el => el.scrollWidth <= el.clientWidth")
            assert page.locator("#avaliacao-form").count() == 0
            page.screenshot(path=str(capturas / f"avaliacao-publicada-{largura}.png"))
            page.unroute("**/api/livros/1984", falhar_consulta)
            page.reload()
            page.locator('.book-card [data-action="detalhes"][data-id="1984"]').click()
            navegador.expect(page.locator("#avaliacao-confirmacao")).to_be_visible()
            outro = browser.new_context(viewport={"width": largura, "height": altura})
            outra_pagina = outro.new_page()
            outra_pagina.goto(url)
            outra_pagina.locator('.book-card [data-action="detalhes"][data-id="1984"]').click()
            navegador.expect(outra_pagina.locator("#book-details .opinion").last).to_contain_text(comentario)
            navegador.expect(outra_pagina.locator("#avaliacao-form")).to_be_visible()
            assert erros == []
            browser.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=5)
