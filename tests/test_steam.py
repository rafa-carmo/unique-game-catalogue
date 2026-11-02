import pytest
import requests
from responses import matchers

from scrappers.steam import APP_DETAILS_URL, BROWSE_ITEMS_URL, SEARCH_RESULTS_URL, STORE_SEARCH_URL, _data_lancamento


def _app(app_id, nome, devs=("Valve",), pubs=("Valve",), **extra):
    data = {
        "steam_appid": app_id,
        "name": nome,
        "is_free": False,
        "price_overview": {"final_formatted": "R$ 33,99"},
        "header_image": f"https://img/{app_id}/header.jpg",
        "screenshots": [{"path_full": f"https://img/{app_id}/ss1.jpg"}],
        "movies": [{"hls_h264": f"https://video/{app_id}/master.m3u8"}],
        "metacritic": {"score": 95},
        "platforms": {"windows": True, "mac": False, "linux": True},
        "pc_requirements": {"minimum": "<strong>Mínimos:</strong><br>Windows 7<br>2 GB RAM"},
        "release_date": {"coming_soon": False, "date": "18 abr. 2011"},
        "supported_languages": "Inglês<strong>*</strong>, Português (Brasil), Espanhol<br><strong>*</strong>idiomas com suporte total de áudio",
        "short_description": "Descrição do jogo",
        "developers": list(devs),
        "publishers": list(pubs),
        "genres": [{"description": "Ação"}, {"description": "Aventura"}],
    }
    data.update(extra)
    return {str(app_id): {"success": True, "data": data}}


def _mock_detalhes(mock_http, app_id, payload):
    mock_http.get(
        APP_DETAILS_URL,
        json=payload,
        match=[matchers.query_param_matcher({"appids": str(app_id), "l": "portuguese"})],
    )


def _mock_busca(mock_http, ids):
    mock_http.get(STORE_SEARCH_URL, json={"items": [{"id": i} for i in ids]})


CAMPOS = {
    "id", "url", "nome", "preco", "imagens", "videos", "score", "plataformas",
    "requisitos_minimos", "data_lancamento", "idiomas", "generos", "descricao", "desenvolvedoras", "distribuidoras",
}


def test_buscar_por_id_retorna_formato_padrao(client, auth, mock_http):
    _mock_detalhes(mock_http, 620, _app(620, "Portal 2"))

    resp = client.get("/steam/buscar?id=620", headers=auth)

    assert resp.status_code == 200
    jogos = resp.json()
    assert len(jogos) == 1
    assert set(jogos[0]) == CAMPOS
    assert jogos[0] == {
        "id": 620,
        "url": "https://store.steampowered.com/app/620",
        "nome": "Portal 2",
        "preco": "R$ 33,99",
        "imagens": ["https://img/620/header.jpg", "https://img/620/ss1.jpg"],
        "videos": ["https://video/620/master.m3u8"],
        "score": 95,
        "plataformas": ["Windows", "Linux"],
        "requisitos_minimos": "Mínimos:\nWindows 7\n2 GB RAM",
        "data_lancamento": "2011-04-18",
        "idiomas": ["Inglês", "Português (Brasil)", "Espanhol"],
        "generos": ["Ação", "Aventura"],
        "descricao": "Descrição do jogo",
        "desenvolvedoras": ["Valve"],
        "distribuidoras": ["Valve"],
    }


def test_buscar_por_id_inexistente_retorna_lista_vazia(client, auth, mock_http):
    _mock_detalhes(mock_http, 999, {"999": {"success": False}})
    resp = client.get("/steam/buscar?id=999", headers=auth)
    assert resp.status_code == 200
    assert resp.json() == []


def test_jogo_gratuito_e_sem_metacritic(client, auth, mock_http):
    payload = _app(10, "Gratis", is_free=True, metacritic=None, price_overview=None)
    _mock_detalhes(mock_http, 10, payload)

    jogo = client.get("/steam/buscar?id=10", headers=auth).json()[0]

    assert jogo["preco"] == "Gratuito"
    assert jogo["score"] is None


def test_generos_vazios_quando_nao_informados(client, auth, mock_http):
    _mock_detalhes(mock_http, 10, _app(10, "Sem gêneros", genres=None))

    jogo = client.get("/steam/buscar?id=10", headers=auth).json()[0]

    assert jogo["generos"] == []


def test_buscar_por_nome_retorna_todos_os_resultados(client, auth, mock_http):
    _mock_busca(mock_http, [620, 400])
    _mock_detalhes(mock_http, 620, _app(620, "Portal 2"))
    _mock_detalhes(mock_http, 400, _app(400, "Portal"))

    resp = client.get("/steam/buscar?name=portal", headers=auth)

    assert resp.status_code == 200
    assert [j["id"] for j in resp.json()] == [620, 400]


def test_buscar_por_nome_ignora_jogos_sem_detalhes(client, auth, mock_http):
    _mock_busca(mock_http, [620, 1])
    _mock_detalhes(mock_http, 620, _app(620, "Portal 2"))
    _mock_detalhes(mock_http, 1, {"1": {"success": False}})

    resp = client.get("/steam/buscar?name=portal", headers=auth)

    assert [j["id"] for j in resp.json()] == [620]


def test_filtro_developer_e_publisher(client, auth, mock_http):
    _mock_busca(mock_http, [1, 2])
    _mock_detalhes(mock_http, 1, _app(1, "A", devs=["Valve"], pubs=["Valve"]))
    _mock_detalhes(mock_http, 2, _app(2, "B", devs=["Outra"], pubs=["Editora X"]))

    por_dev = client.get("/steam/buscar?name=x&developer=VALVE", headers=auth).json()
    por_pub = client.get("/steam/buscar?name=x&publisher=editora", headers=auth).json()
    nenhum = client.get("/steam/buscar?name=x&developer=Valve&publisher=Editora", headers=auth).json()

    assert [j["id"] for j in por_dev] == [1]
    assert [j["id"] for j in por_pub] == [2]
    assert nenhum == []


def test_id_com_name_filtra_pelo_nome(client, auth, mock_http):
    _mock_detalhes(mock_http, 620, _app(620, "Portal 2"))

    assert len(client.get("/steam/buscar?id=620&name=portal", headers=auth).json()) == 1
    assert client.get("/steam/buscar?id=620&name=zelda", headers=auth).json() == []


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("18 abr. 2011", "2011-04-18"),
        ("1 de mar. de 2020", "2020-03-01"),
        ("5 dez 2019", "2019-12-05"),
        ("Em breve", "Em breve"),
        ("", None),
    ],
)
def test_data_lancamento_normalizada(entrada, esperado):
    assert _data_lancamento({"date": entrada}) == esperado


def test_data_e_idiomas_ausentes(client, auth, mock_http):
    payload = _app(11, "Sem dados", release_date=None, supported_languages=None)
    _mock_detalhes(mock_http, 11, payload)

    jogo = client.get("/steam/buscar?id=11", headers=auth).json()[0]

    assert jogo["data_lancamento"] is None
    assert jogo["idiomas"] == []


def test_exige_api_key_em_gratuitos(client):
    assert client.get("/steam/gratuitos").status_code == 401


def test_gratuitos_lista_apenas_100_por_cento_de_desconto(client, auth, mock_http):
    mock_http.get(
        SEARCH_RESULTS_URL,
        json={
            "items": [
                {"name": "A", "logo": "https://cdn/steam/apps/1/hash/capsule.jpg?t=1"},
                {"name": "B", "logo": "https://cdn/steam/apps/2/hash/capsule.jpg?t=1"},
                {"name": "Sem id", "logo": "https://cdn/outro.jpg"},
            ]
        },
    )
    gratis = _app(1, "A", price_overview={"final_formatted": "Gratuito", "discount_percent": 100})
    desconto = _app(2, "B", price_overview={"final_formatted": "R$ 5,00", "discount_percent": 50})
    _mock_detalhes(mock_http, 1, gratis)
    _mock_detalhes(mock_http, 2, desconto)
    mock_http.get(
        BROWSE_ITEMS_URL,
        json={"response": {"store_items": [
            {"appid": 1, "best_purchase_option": {"free_to_keep_ends": 1793642400}},
        ]}},
    )

    resp = client.get("/steam/gratuitos", headers=auth)

    assert resp.status_code == 200
    jogos = resp.json()
    assert [j["id"] for j in jogos] == [1]
    assert set(jogos[0]) == CAMPOS | {"inicio_promocao", "fim_promocao"}
    assert jogos[0]["url"] == "https://store.steampowered.com/app/1"
    assert jogos[0]["inicio_promocao"] is None
    assert jogos[0]["fim_promocao"] == "2026-11-02T18:00:00.000Z"


def test_gratuitos_sem_resultados_retorna_lista_vazia(client, auth, mock_http):
    mock_http.get(SEARCH_RESULTS_URL, json={"items": []})
    assert client.get("/steam/gratuitos", headers=auth).json() == []


def test_sem_id_e_sem_name_retorna_400(client, auth, mock_http):
    resp = client.get("/steam/buscar?developer=Valve", headers=auth)
    assert resp.status_code == 400
    assert "id" in resp.json()["detail"]


def test_id_invalido_retorna_422(client, auth):
    assert client.get("/steam/buscar?id=abc", headers=auth).status_code == 422


def test_erro_da_steam_propaga_excecao(client, auth, mock_http):
    mock_http.get(APP_DETAILS_URL, status=500)
    with pytest.raises(requests.HTTPError):
        client.get("/steam/buscar?id=620", headers=auth)
