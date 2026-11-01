from datetime import datetime, timedelta, timezone

from scrappers.epic_games import FREE_GAMES_URL

CAMPOS = {
    "id", "nome", "preco", "imagens", "videos", "score", "plataformas",
    "requisitos_minimos", "data_lancamento", "idiomas", "descricao",
    "desenvolvedoras", "distribuidoras", "inicio_promocao", "fim_promocao", "url",
}


def _iso(delta_dias: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=delta_dias)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _oferta(inicio: int, fim: int, percentual: int = 0) -> dict:
    return {
        "startDate": _iso(inicio),
        "endDate": _iso(fim),
        "discountSetting": {"discountType": "PERCENTAGE", "discountPercentage": percentual},
    }


def _item(titulo, atuais=(), proximas=(), **extra):
    item = {
        "id": f"id-{titulo}",
        "title": titulo,
        "description": f"Descrição de {titulo}",
        "effectiveDate": "2021-02-16T17:00:00.000Z",
        "seller": {"name": "Vendedor"},
        "productSlug": f"{titulo.lower()}/home",
        "customAttributes": [
            {"key": "developerName", "value": "Dev Studio"},
            {"key": "publisherName", "value": "Pub Games"},
        ],
        "keyImages": [
            {"type": "OfferImageWide", "url": f"https://cdn/{titulo}/wide.jpg"},
            {"type": "Thumbnail", "url": f"https://cdn/{titulo}/wide.jpg"},
            {"type": "heroCarouselVideo", "url": "com.epicgames.video://abc"},
            {"type": "featuredMedia", "url": f"https://cdn/{titulo}/m1.jpg"},
        ],
        "promotions": {
            "promotionalOffers": [{"promotionalOffers": list(atuais)}] if atuais else [],
            "upcomingPromotionalOffers": [{"promotionalOffers": list(proximas)}] if proximas else [],
        },
    }
    item.update(extra)
    return item


def _mock(mock_http, elementos):
    mock_http.get(
        FREE_GAMES_URL,
        json={"data": {"Catalog": {"searchStore": {"elements": elementos}}}},
    )


def test_lista_apenas_jogos_gratuitos_agora(client, auth, mock_http):
    _mock(
        mock_http,
        [
            _item("Gratis", atuais=[_oferta(-1, 6)]),
            _item("Desconto", atuais=[_oferta(-1, 6, percentual=40)]),
            _item("Proximo", proximas=[_oferta(3, 10)]),
            _item("Expirado", atuais=[_oferta(-10, -3)]),
            _item("SemPromocao"),
        ],
    )

    resp = client.get("/epic/gratuitos", headers=auth)

    assert resp.status_code == 200
    assert [j["nome"] for j in resp.json()] == ["Gratis"]


def test_formato_do_retorno(client, auth, mock_http):
    oferta = _oferta(-1, 6)
    _mock(mock_http, [_item("Gratis", atuais=[oferta])])

    jogo = client.get("/epic/gratuitos", headers=auth).json()[0]

    assert set(jogo) == CAMPOS
    assert jogo == {
        "id": "id-Gratis",
        "nome": "Gratis",
        "preco": "Gratuito",
        "imagens": ["https://cdn/Gratis/wide.jpg", "https://cdn/Gratis/m1.jpg"],
        "videos": [],
        "score": None,
        "plataformas": [],
        "requisitos_minimos": None,
        "data_lancamento": "2021-02-16",
        "idiomas": [],
        "descricao": "Descrição de Gratis",
        "desenvolvedoras": ["Dev Studio"],
        "distribuidoras": ["Pub Games"],
        "inicio_promocao": oferta["startDate"],
        "fim_promocao": oferta["endDate"],
        "url": "https://store.epicgames.com/pt-BR/p/gratis",
    }


def test_promocao_com_duas_janelas_considera_a_gratuita(client, auth, mock_http):
    item = _item("Duas", atuais=[_oferta(-5, 2, percentual=70), _oferta(-1, 6)])
    _mock(mock_http, [item])

    jogos = client.get("/epic/gratuitos", headers=auth).json()

    assert [j["nome"] for j in jogos] == ["Duas"]


def test_usa_vendedor_e_slug_alternativos(client, auth, mock_http):
    item = _item(
        "Alt",
        atuais=[_oferta(-1, 6)],
        customAttributes=[],
        productSlug=None,
        offerMappings=[{"pageSlug": "alt-123", "pageType": "productHome"}],
    )
    _mock(mock_http, [item])

    jogo = client.get("/epic/gratuitos", headers=auth).json()[0]

    assert jogo["desenvolvedoras"] == ["Vendedor"]
    assert jogo["distribuidoras"] == ["Vendedor"]
    assert jogo["url"] == "https://store.epicgames.com/pt-BR/p/alt-123"


def test_sem_jogos_gratuitos_retorna_lista_vazia(client, auth, mock_http):
    _mock(mock_http, [])
    resp = client.get("/epic/gratuitos", headers=auth)
    assert resp.status_code == 200
    assert resp.json() == []


def test_exige_api_key(client):
    assert client.get("/epic/gratuitos").status_code == 401
