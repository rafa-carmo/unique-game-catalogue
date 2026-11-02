from fastapi import APIRouter, HTTPException

from scrappers import gog_game

router = APIRouter(prefix="/gog", tags=["gog"])


@router.get("/gratuitos")
def gratuitos():
    return gog_game.gratuitos()


@router.get("/buscar")
def buscar(
    id: int | None = None,
    name: str | None = None,
    developer: str | None = None,
    publisher: str | None = None,
):
    try:
        return gog_game.buscar(id=id, name=name, developer=developer, publisher=publisher)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
