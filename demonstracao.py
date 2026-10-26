"""Dados iniciais ilustrativos usados na composição da livraria."""

from datetime import timedelta


def livros_iniciais():
    return [
        {"id": "1984", "titulo": "1984", "autor": "George Orwell", "ano": 1949,
         "genero": "Distopia", "estoque": 3, "lancamento": False, "preco": 49.90,
         "codigo": "9788535914849", "secao": "Literatura", "prateleira": "A1",
         "sinopse": "Uma sociedade sob vigilância. Um clássico sobre liberdade, memória e poder.",
         "avaliacoes": [{"cliente": "Marina", "texto": "Uma leitura marcante."}]},
        {"id": "bichos", "titulo": "A Revolução dos Bichos", "autor": "George Orwell",
         "ano": 1945, "genero": "Distopia", "estoque": 2, "lancamento": False,
         "preco": 39.90, "codigo": "9788535909555", "secao": "Literatura", "prateleira": "A1",
         "sinopse": "Uma fábula sobre os animais de uma fazenda e os rumos de sua revolução.",
         "avaliacoes": [{"cliente": "Pedro", "texto": "Curto, envolvente e cheio de reflexões."}]},
        {"id": "hobbit", "titulo": "O Hobbit", "autor": "J.R.R. Tolkien", "ano": 1937,
         "genero": "Fantasia", "estoque": 5, "lancamento": False, "preco": 69.90,
         "codigo": "9788595084742", "secao": "Fantasia", "prateleira": "B2",
         "sinopse": "Bilbo Bolseiro deixa o conforto de casa para uma aventura inesperada.",
         "avaliacoes": [{"cliente": "Luiza", "texto": "Uma aventura para reler muitas vezes."}]},
        {"id": "reino", "titulo": "O Novo Reino", "autor": "Ana Silva", "ano": 2026,
         "genero": "Fantasia", "estoque": 4, "lancamento": True, "preco": 54.90,
         "codigo": "9780000000001", "secao": "Lançamentos", "prateleira": "L1",
         "sinopse": "Uma jornada por um reino que começa a descobrir suas próprias histórias.",
         "avaliacoes": []},
        {"id": "esgotado", "titulo": "Livro Esgotado", "autor": "Autor Exemplo", "ano": 2025,
         "genero": "Romance", "estoque": 0, "lancamento": False, "preco": 44.90,
         "codigo": "9780000000002", "secao": "Romances", "prateleira": "C3",
         "sinopse": "Um título de demonstração para acompanhar a reposição de estoque.",
         "avaliacoes": []},
    ]


def preencher_demonstracao(loja):
    loja.configurar_loja("Seg–Sáb, 09h às 19h", 12)
    agora = loja.agora()
    loja.oferecer_horario("Carlos · Literatura e clássicos", (agora + timedelta(days=1)).isoformat())
    loja.oferecer_horario("Lia · Fantasia e ficção", (agora + timedelta(days=2)).isoformat())
    loja.cadastrar_evento("Conversa com autores", (agora + timedelta(days=3)).isoformat(),
                         "Salão da livraria", capacidade=20,
                         lembrar_em=(agora + timedelta(days=2)).isoformat())
    loja.cadastrar_evento("Encontro do clube de leitura", (agora + timedelta(days=7)).isoformat(),
                         "Sala de leitura", capacidade=12,
                         lembrar_em=(agora + timedelta(days=6)).isoformat())
    loja.criar_clube("Leituras compartilhadas")
    return loja


def criar_demonstracao():
    from infrastructure.composition import Livraria
    return preencher_demonstracao(Livraria(livros_iniciais()))
