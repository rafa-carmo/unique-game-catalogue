import re

import requests

CATALOG_URL = "https://catalog.gog.com/v1/catalog"
GAME_URL = "https://api.gog.com/v2/games/{id}"
STORE_GAME_URL = "https://www.gog.com/en/game/{slug}"
TIMEOUT = 15
MAX_RESULTS = 10
PLATAFORMAS = {"windows": "Windows", "osx": "Mac", "linux": "Linux"}


def _texto(html: str | None) -> str | None:
    if not html:
        return None
    html = re.sub(r"<video.*?</video>", "", html, flags=re.S)
    html = re.sub(r"<br\s*/?>|</p>|</li>", "\n", html)
    return re.sub(r"<[^>]+>", "", html).strip()


def _descricao(overview: str | None) -> str | None:
    texto = _texto(overview)
    if not texto:
        return None
    return next((p.strip() for p in texto.split("\n") if p.strip()), None)


def _catalogo(**params) -> list[dict]:
    resp = requests.get(
        CATALOG_URL,
        params={"countryCode": "BR", "currencyCode": "BRL", **params},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("products", [])


def _requisitos_minimos(game: dict) -> str | None:
    for so in game.get("_embedded", {}).get("supportedOperatingSystems", []):
        for req in so.get("systemRequirements", []):
            if req.get("type") == "minimum" and req.get("requirements"):
                return "\n".join(
                    f"{r['name']} {r['description']}" for r in req["requirements"]
                )
    return None


def _idiomas(emb: dict) -> list[str]:
    nomes = []
    for loc in emb.get("localizations", []):
        nome = loc.get("_embedded", {}).get("language", {}).get("name")
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def _data_lancamento(product: dict) -> str | None:
    data = product.get("globalReleaseDate") or product.get("gogReleaseDate")
    return data[:10] if data else None


def _detalhes(app_id: int, item: dict | None = None) -> dict | None:
    resp = requests.get(
        GAME_URL.format(id=app_id), params={"locale": "pt-BR"}, timeout=TIMEOUT
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    game = resp.json()
    emb = game.get("_embedded", {})
    titulo = emb.get("product", {}).get("title")

    if item is None:
        item = next(
            (p for p in _catalogo(query=f"like:{titulo}", limit=MAX_RESULTS) if int(p["id"]) == app_id),
            {},
        )

    imagens = [item["coverHorizontal"]] if item.get("coverHorizontal") else []
    imagens += [s.replace("{formatter}", "1600") for s in item.get("screenshots", [])]
    videos = [
        v["_links"]["self"]["href"]
        for v in emb.get("videos", [])
        if v.get("_links", {}).get("self")
    ]
    preco = (item.get("price") or {}).get("final")
    rating = item.get("reviewsRating")
    return {
        "id": app_id,
        "url": STORE_GAME_URL.format(slug=item["slug"]) if item.get("slug") else None,
        "nome": titulo,
        "preco": preco,
        "imagens": imagens,
        "videos": videos,
        # reviewsRating da GOG é de 0 a 50; convertido para 0 a 100
        "score": rating * 2 if rating else None,
        "plataformas": [
            PLATAFORMAS[o] for o in item.get("operatingSystems", []) if o in PLATAFORMAS
        ],
        "requisitos_minimos": _requisitos_minimos(game),
        "data_lancamento": _data_lancamento(emb.get("product", {})),
        "idiomas": _idiomas(emb),
        "generos": [g["name"] for g in (emb.get("genres") or []) if g.get("name")],
        "descricao": _descricao(game.get("overview")),
        "desenvolvedoras": [d["name"] for d in emb.get("developers", [])],
        "distribuidoras": [p["name"] for p in emb.get("publishers", [])],
    }


def _contem(valores: list[str], termo: str) -> bool:
    return any(termo.lower() in v.lower() for v in valores)


def buscar(
    id: int | None = None,
    name: str | None = None,
    developer: str | None = None,
    publisher: str | None = None,
) -> list[dict]:
    """Busca jogos na GOG. Os filtros informados são combinados (AND).

    Sem `id`, é necessário `name` para localizar os candidatos; os filtros de
    developer e publisher são aplicados sobre os detalhes de cada jogo.
    """
    if id is not None:
        jogo = _detalhes(id)
        candidatos = [jogo] if jogo else []
        if name:
            candidatos = [j for j in candidatos if name.lower() in (j["nome"] or "").lower()]
    elif name:
        candidatos = []
        for item in _catalogo(query=name, limit=MAX_RESULTS, productType="in:game,pack"):
            jogo = _detalhes(int(item["id"]), item)
            if jogo:
                candidatos.append(jogo)
    else:
        raise ValueError("Informe ao menos 'id' ou 'name'.")

    if developer:
        candidatos = [j for j in candidatos if _contem(j["desenvolvedoras"], developer)]
    if publisher:
        candidatos = [j for j in candidatos if _contem(j["distribuidoras"], publisher)]
    return candidatos
