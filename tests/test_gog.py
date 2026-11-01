import re

from responses import matchers

from scrappers.gog_game import CATALOG_URL

GAME_URL_RE = re.compile(r"https://api\.gog\.com/v2/games/(\d+)")


def _game(titulo, devs=("CD PROJEKT RED",), pubs=("CD PROJEKT RED",), videos=True):
    return {
        "overview": "<p>Primeiro parágrafo.<br>\n<br>\n<video><source src='x.mp4'></video></p><p>Segundo.</p>",
        "_embedded": {
            "product": {"title": titulo, "globalReleaseDate": "2007-10-26T00:00:00+02:00"},
            "localizations": [
                {"_embedded": {"language": {"name": nome}, "localizationScope": {"type": tipo}}}
                for nome in ("English", "German")
                for tipo in ("audio", "text")
            ],
            "developers": [{"name": d} for d in devs],
            "publishers": [{"name": p} for p in pubs],
            "genres": [{"name": "RPG"}, {"name": "Aventura"}],
            "videos": (
                [{"_links": {"self": {"href": "https://www.youtube.com/embed/abc"}}}]
                if videos
                else []
            ),
            "supportedOperatingSystems": [
                {
                    "operatingSystem": {"name": "windows"},
                    "systemRequirements": [
                        {
                            "type": "minimum",
                            "requirements": [
                                {"id": "system", "name": "System:", "description": "Windows 10"},
                                {"id": "memory", "name": "Memory:", "description": "2 GB RAM"},
                            ],
                        }
                    ],
                }
            ],
        },
    }


def _item(app_id, titulo="Jogo", rating=46, os_=("windows", "osx")):
    return {
        "id": str(app_id),
        "title": titulo,
        "coverHorizontal": f"https://img/{app_id}/cover.png",
        "screenshots": [f"https://img/{app_id}/s1_{{formatter}}.jpg"],
        "operatingSystems": list(os_),
        "price": {"final": "R$ 2,55"},
        "reviewsRating": rating,
    }


def _mock_jogo(mock_http, app_id, game):
    mock_http.get(f"https://api.gog.com/v2/games/{app_id}", json=game)


def _mock_catalogo(mock_http, itens, query=None):
    match = [matchers.query_param_matcher({"query": query}, strict_match=False)] if query else []
    mock_http.get(CATALOG_URL, json={"products": itens}, match=match)


CAMPOS = {
    "id", "nome", "preco", "imagens", "videos", "score", "plataformas",
    "requisitos_minimos", "data_lancamento", "idiomas", "generos", "descricao", "desenvolvedoras", "distribuidoras",
}


def test_buscar_por_id_retorna_formato_padrao(client, auth, mock_http):
    _mock_jogo(mock_http, 100, _game("The Witcher"))
    _mock_catalogo(mock_http, [_item(100, "The Witcher")], query="like:The Witcher")

    resp = client.get("/gog/buscar?id=100", headers=auth)

    assert resp.status_code == 200
    jogos = resp.json()
    assert len(jogos) == 1
    assert set(jogos[0]) == CAMPOS
    assert jogos[0] == {
        "id": 100,
        "nome": "The Witcher",
        "preco": "R$ 2,55",
        "imagens": ["https://img/100/cover.png", "https://img/100/s1_1600.jpg"],
        "videos": ["https://www.youtube.com/embed/abc"],
        "score": 92,
        "plataformas": ["Windows", "Mac"],
        "requisitos_minimos": "System: Windows 10\nMemory: 2 GB RAM",
        "data_lancamento": "2007-10-26",
        "idiomas": ["English", "German"],
        "generos": ["RPG", "Aventura"],
        "descricao": "Primeiro parágrafo.",
        "desenvolvedoras": ["CD PROJEKT RED"],
        "distribuidoras": ["CD PROJEKT RED"],
    }


def test_id_fora_do_catalogo_retorna_campos_vazios(client, auth, mock_http):
    _mock_jogo(mock_http, 1, _game("Fallout Classic", videos=False))
    _mock_catalogo(mock_http, [], query="like:Fallout Classic")

    jogo = client.get("/gog/buscar?id=1", headers=auth).json()[0]

    assert jogo["nome"] == "Fallout Classic"
    assert jogo["preco"] is None
    assert jogo["score"] is None
    assert jogo["imagens"] == []
    assert jogo["plataformas"] == []
    assert jogo["videos"] == []


def test_generos_vazios_quando_nao_informados(client, auth, mock_http):
    game = _game("Sem gêneros")
    game["_embedded"].pop("genres")
    _mock_jogo(mock_http, 100, game)
    _mock_catalogo(mock_http, [_item(100, "Sem gêneros")], query="like:Sem gêneros")

    jogo = client.get("/gog/buscar?id=100", headers=auth).json()[0]

    assert jogo["generos"] == []


def test_id_inexistente_retorna_lista_vazia(client, auth, mock_http):
    mock_http.get("https://api.gog.com/v2/games/999", status=404)
    resp = client.get("/gog/buscar?id=999", headers=auth)
    assert resp.status_code == 200
    assert resp.json() == []


def test_buscar_por_nome_usa_itens_do_catalogo(client, auth, mock_http):
    _mock_catalogo(mock_http, [_item(1, "Witcher 1"), _item(2, "Witcher 2", rating=0)], query="witcher")
    mock_http.get(GAME_URL_RE, json=_game("Witcher"))

    resp = client.get("/gog/buscar?name=witcher", headers=auth)

    assert resp.status_code == 200
    jogos = resp.json()
    assert [j["id"] for j in jogos] == [1, 2]
    assert jogos[0]["score"] == 92
    assert jogos[1]["score"] is None


def test_buscar_por_nome_ignora_jogos_inexistentes(client, auth, mock_http):
    _mock_catalogo(mock_http, [_item(1), _item(2)])
    mock_http.get("https://api.gog.com/v2/games/1", json=_game("Ok"))
    mock_http.get("https://api.gog.com/v2/games/2", status=404)

    resp = client.get("/gog/buscar?name=x", headers=auth)

    assert [j["id"] for j in resp.json()] == [1]


def test_filtro_developer_e_publisher(client, auth, mock_http):
    _mock_catalogo(mock_http, [_item(1), _item(2)])
    mock_http.get("https://api.gog.com/v2/games/1", json=_game("A", ["CD PROJEKT RED"], ["CD PROJEKT RED"]))
    mock_http.get("https://api.gog.com/v2/games/2", json=_game("B", ["Outra"], ["Editora X"]))

    por_dev = client.get("/gog/buscar?name=x&developer=cd%20projekt", headers=auth).json()
    por_pub = client.get("/gog/buscar?name=x&publisher=EDITORA", headers=auth).json()
    nenhum = client.get("/gog/buscar?name=x&developer=Outra&publisher=CD", headers=auth).json()

    assert [j["id"] for j in por_dev] == [1]
    assert [j["id"] for j in por_pub] == [2]
    assert nenhum == []


def test_id_com_name_filtra_pelo_nome(client, auth, mock_http):
    _mock_jogo(mock_http, 100, _game("The Witcher"))
    _mock_catalogo(mock_http, [_item(100, "The Witcher")])

    assert len(client.get("/gog/buscar?id=100&name=witcher", headers=auth).json()) == 1
    assert client.get("/gog/buscar?id=100&name=zelda", headers=auth).json() == []


def test_sem_id_e_sem_name_retorna_400(client, auth, mock_http):
    resp = client.get("/gog/buscar?publisher=x", headers=auth)
    assert resp.status_code == 400
    assert "id" in resp.json()["detail"]


def test_id_invalido_retorna_422(client, auth):
    assert client.get("/gog/buscar?id=abc", headers=auth).status_code == 422
