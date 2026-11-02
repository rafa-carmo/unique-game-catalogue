from fastapi import APIRouter, HTTPException

from scrappers import steam

router = APIRouter(prefix="/steam", tags=["steam"])


@router.get("/gratuitos")
def gratuitos():
    return steam.gratuitos()


@router.get("/buscar")
def buscar(
    id: int | None = None,
    name: str | None = None,
    developer: str | None = None,
    publisher: str | None = None,
):
    try:
        return steam.buscar(id=id, name=name, developer=developer, publisher=publisher)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
