from fastapi import APIRouter

from scrappers import epic_games

router = APIRouter(prefix="/epic", tags=["epic"])


@router.get("/gratuitos")
def gratuitos():
    return epic_games.gratuitos()
