import re

import requests

STORE_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
STORE_GAME_URL = "https://store.steampowered.com/app/{id}"
SEARCH_RESULTS_URL = "https://store.steampowered.com/search/results/"
TIMEOUT = 15
MAX_GRATUITOS = 50


def _texto(html: str | None) -> str | None:
    if not html:
        return None
    html = re.sub(r"<br\s*/?>|</li>", "\n", html)
    return re.sub(r"<[^>]+>", "", html).strip()


MESES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _data_lancamento(release_date: dict | None) -> str | None:
    """Converte '18 abr. 2011' para '2011-04-18'; devolve o texto original se não reconhecer."""
    texto = ((release_date or {}).get("date") or "").strip()
    if not texto:
        return None
    m = re.fullmatch(r"(\d{1,2}) (?:de )?([a-zç]{3})[a-zç]*\.?,? (?:de )?(\d{4})", texto.lower())
    if m and m.group(2) in MESES:
        return f"{m.group(3)}-{MESES[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return texto


def _idiomas(html: str | None) -> list[str]:
    if not html:
        return []
    html = html.split("<br>")[0]
    texto = re.sub(r"<[^>]+>", "", html).replace("*", "")
    return [i.strip() for i in texto.split(",") if i.strip()]


def _dados(app_id: int) -> dict | None:
    resp = requests.get(
        APP_DETAILS_URL, params={"appids": app_id, "l": "portuguese"}, timeout=TIMEOUT
    )
    resp.raise_for_status()
    entrada = resp.json().get(str(app_id), {})
    if not entrada.get("success"):
        return None
    return entrada["data"]


def _detalhes(app_id: int) -> dict | None:
    d = _dados(app_id)
    return _formatar(d, app_id) if d else None


def _formatar(d: dict, app_id: int) -> dict:
    plataformas = [
        nome
        for chave, nome in (("windows", "Windows"), ("mac", "Mac"), ("linux", "Linux"))
        if (d.get("platforms") or {}).get(chave)
    ]
    imagens = [d["header_image"]] if d.get("header_image") else []
    imagens += [s["path_full"] for s in d.get("screenshots", [])]
    videos = [
        m.get("hls_h264") or (m.get("mp4") or {}).get("max")
        for m in d.get("movies", [])
        if m.get("hls_h264") or (m.get("mp4") or {}).get("max")
    ]
    requisitos = d.get("pc_requirements")
    minimos = requisitos.get("minimum") if isinstance(requisitos, dict) else None
    return {
        "id": d.get("steam_appid"),
        "url": STORE_GAME_URL.format(id=app_id),
        "nome": d.get("name"),
        "preco": (
            "Gratuito"
            if d.get("is_free")
            else (d.get("price_overview") or {}).get("final_formatted")
        ),
        "imagens": imagens,
        "videos": videos,
        "score": (d.get("metacritic") or {}).get("score"),
        "plataformas": plataformas,
        "requisitos_minimos": _texto(minimos),
        "data_lancamento": _data_lancamento(d.get("release_date")),
        "idiomas": _idiomas(d.get("supported_languages")),
        "generos": [g["description"] for g in (d.get("genres") or []) if g.get("description")],
        "descricao": d.get("short_description"),
        "desenvolvedoras": d.get("developers", []),
        "distribuidoras": d.get("publishers", []),
    }


def gratuitos() -> list[dict]:
    """Lista os jogos com 100% de desconto agora na Steam (Brasil)."""
    resp = requests.get(
        SEARCH_RESULTS_URL,
        params={
            "query": "", "start": 0, "count": MAX_GRATUITOS, "specials": 1,
            "maxprice": "free", "json": 1, "cc": "BR", "l": "portuguese",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    jogos = []
    for item in resp.json().get("items", []):
        m = re.search(r"/apps/(\d+)/", item.get("logo") or "")
        if not m:
            continue
        d = _dados(int(m.group(1)))
        if d and (d.get("price_overview") or {}).get("discount_percent") == 100:
            jogos.append(_formatar(d, int(m.group(1))))
    return jogos


def _contem(valores: list[str], termo: str) -> bool:
    return any(termo.lower() in v.lower() for v in valores)


def buscar(
    id: int | None = None,
    name: str | None = None,
    developer: str | None = None,
    publisher: str | None = None,
) -> list[dict]:
    """Busca jogos na Steam. Os filtros informados são combinados (AND).

    Sem `id`, é necessário `name` para localizar os candidatos; os filtros de
    developer e publisher são aplicados sobre os detalhes de cada jogo.
    """
    if id is not None:
        jogo = _detalhes(id)
        candidatos = [jogo] if jogo else []
        if name:
            candidatos = [j for j in candidatos if name.lower() in (j["nome"] or "").lower()]
    elif name:
        resp = requests.get(
            STORE_SEARCH_URL, params={"term": name, "l": "portuguese", "cc": "BR"}, timeout=TIMEOUT
        )
        resp.raise_for_status()
        candidatos = []
        for item in resp.json().get("items", []):
            jogo = _detalhes(item["id"])
            if jogo:
                candidatos.append(jogo)
    else:
        raise ValueError("Informe ao menos 'id' ou 'name'.")

    if developer:
        candidatos = [j for j in candidatos if _contem(j["desenvolvedoras"], developer)]
    if publisher:
        candidatos = [j for j in candidatos if _contem(j["distribuidoras"], publisher)]
    return candidatos
