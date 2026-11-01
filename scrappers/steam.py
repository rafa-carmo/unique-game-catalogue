import re

import requests

STORE_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
TIMEOUT = 15


def _texto(html: str | None) -> str | None:
    if not html:
        return None
    html = re.sub(r"<br\s*/?>|</li>", "\n", html)
    return re.sub(r"<[^>]+>", "", html).strip()


def _detalhes(app_id: int) -> dict | None:
    resp = requests.get(
        APP_DETAILS_URL, params={"appids": app_id, "l": "portuguese"}, timeout=TIMEOUT
    )
    resp.raise_for_status()
    entrada = resp.json().get(str(app_id), {})
    if not entrada.get("success"):
        return None
    d = entrada["data"]
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
        "descricao": d.get("short_description"),
        "desenvolvedoras": d.get("developers", []),
        "distribuidoras": d.get("publishers", []),
    }


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
