import re
import secrets
import sys
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"


def gerar_api_key(env_path: Path = ENV_PATH) -> str:
    chave = secrets.token_hex(32)
    linha = f"API_KEY={chave}"
    conteudo = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

    if re.search(r"^API_KEY=.*$", conteudo, flags=re.M):
        conteudo = re.sub(r"^API_KEY=.*$", linha, conteudo, flags=re.M)
    else:
        conteudo = conteudo.rstrip("\n") + ("\n" if conteudo else "") + linha + "\n"

    env_path.write_text(conteudo, encoding="utf-8")
    return chave


if __name__ == "__main__":
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else ENV_PATH
    print(f"API_KEY gerada e salva em {caminho}:")
    print(gerar_api_key(caminho))
