import pytest

ROTAS = ["/", "/items/1", "/steam/buscar?id=620", "/gog/buscar?id=1"]


@pytest.mark.parametrize("rota", ROTAS)
def test_sem_api_key_retorna_401(client, rota):
    assert client.get(rota).status_code == 401


@pytest.mark.parametrize("rota", ROTAS)
def test_api_key_invalida_retorna_401(client, rota):
    assert client.get(rota, headers={"X-API-Key": "errada"}).status_code == 401


def test_api_key_valida_acessa_raiz(client, auth):
    resp = client.get("/", headers=auth)
    assert resp.status_code == 200
    assert resp.json() == {"Hello": "World"}


def test_items_retorna_parametros(client, auth):
    resp = client.get("/items/7?q=teste", headers=auth)
    assert resp.status_code == 200
    assert resp.json() == {"item_id": 7, "q": "teste"}


@pytest.mark.parametrize("valor", [None, "", "your_api_key_here"])
def test_servidor_sem_api_key_configurada_retorna_500(client, monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv("API_KEY")
    else:
        monkeypatch.setenv("API_KEY", valor)
    resp = client.get("/", headers={"X-API-Key": "qualquer"})
    assert resp.status_code == 500
