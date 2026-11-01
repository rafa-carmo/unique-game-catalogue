from fastapi import FastAPI

from routes.gog import router as gog_router
from routes.steam import router as steam_router

app = FastAPI()
app.include_router(steam_router)
app.include_router(gog_router)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}