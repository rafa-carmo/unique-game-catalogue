from datetime import datetime, timezone

import requests

FREE_GAMES_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
STORE_URL = "https://store.epicgames.com/pt-BR/p/{slug}"
TIMEOUT = 15


def _data(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def _janela_gratuita(item: dict, agora: datetime) -> dict | None:
    """Retorna a janela de promoção com 100% de desconto em vigor, se houver."""
    grupos = (item.get("promotions") or {}).get("promotionalOffers") or []
    for grupo in grupos:
        for oferta in grupo.get("promotionalOffers", []):
            if (oferta.get("discountSetting") or {}).get("discountPercentage") != 0:
                continue
            if _data(oferta["startDate"]) <= agora <= _data(oferta["endDate"]):
                return oferta
    return None


def _atributo(item: dict, chave: str) -> str | None:
    return next(
        (a["value"] for a in item.get("customAttributes") or [] if a.get("key") == chave),
        None,
    )


def _slug(item: dict) -> str | None:
    slug = item.get("productSlug")
    if not slug:
        mapeamentos = item.get("offerMappings") or (item.get("catalogNs") or {}).get("mappings") or []
        slug = next((m["pageSlug"] for m in mapeamentos if m.get("pageSlug")), None)
    slug = slug or item.get("urlSlug")
    return slug.split("/")[0] if slug else None


def _formatar(item: dict, janela: dict) -> dict:
    imagens = []
    for img in item.get("keyImages") or []:
        url = img.get("url")
        if url and url.startswith("http") and url not in imagens:
            imagens.append(url)
    slug = _slug(item)
    seller = (item.get("seller") or {}).get("name")
    return {
        "id": item.get("id"),
        "nome": item.get("title"),
        "preco": "Gratuito",
        "imagens": imagens,
        "videos": [],
        "score": None,
        "plataformas": [],
        "requisitos_minimos": None,
        "data_lancamento": (item.get("effectiveDate") or "")[:10] or None,
        "idiomas": [],
        "descricao": item.get("description"),
        "desenvolvedoras": [_atributo(item, "developerName") or seller] if (_atributo(item, "developerName") or seller) else [],
        "distribuidoras": [_atributo(item, "publisherName") or seller] if (_atributo(item, "publisherName") or seller) else [],
        "inicio_promocao": janela["startDate"],
        "fim_promocao": janela["endDate"],
        "url": STORE_URL.format(slug=slug) if slug else None,
    }


def gratuitos() -> list[dict]:
    """Lista os jogos que estão gratuitos agora na Epic Games Store (Brasil)."""
    resp = requests.get(
        FREE_GAMES_URL,
        params={"locale": "pt-BR", "country": "BR", "allowCountries": "BR"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    elementos = resp.json()["data"]["Catalog"]["searchStore"]["elements"]
    agora = datetime.now(timezone.utc)
    jogos = []
    for item in elementos:
        janela = _janela_gratuita(item, agora)
        if janela:
            jogos.append(_formatar(item, janela))
    return jogos
