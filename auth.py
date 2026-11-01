import os
import secrets

from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

load_dotenv()

PLACEHOLDER = "your_api_key_here"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verificar_api_key(api_key: str | None = Security(api_key_header)) -> None:
    esperada = os.getenv("API_KEY")
    if not esperada or esperada == PLACEHOLDER:
        raise HTTPException(status_code=500, detail="API_KEY não configurada no servidor.")
    if not api_key or not secrets.compare_digest(api_key, esperada):
        raise HTTPException(status_code=401, detail="API key inválida ou ausente.")
