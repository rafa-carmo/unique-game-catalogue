import os

os.environ["API_KEY"] = "chave-de-teste"

import pytest
import responses as responses_lib
from fastapi.testclient import TestClient

from main import app

API_KEY = os.environ["API_KEY"]


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth():
    return {"X-API-Key": API_KEY}


@pytest.fixture
def mock_http():
    """Bloqueia qualquer requisição HTTP não mockada explicitamente."""
    with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps
