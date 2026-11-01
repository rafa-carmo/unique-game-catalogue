# Game Scrapper

API REST em FastAPI que busca jogos na **Steam** e na **GOG** e devolve os dados em um formato único.

![Python](https://img.shields.io/badge/Python-%E2%89%A5%203.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-%E2%89%A5%200.162.0-009688?logo=fastapi&logoColor=white)
![Requests](https://img.shields.io/badge/Requests-%E2%89%A5%202.31.0-2C5BB4)
![python-dotenv](https://img.shields.io/badge/python--dotenv-%E2%89%A5%201.0.0-ECD53F)
![uv](https://img.shields.io/badge/uv-gerenciador%20de%20pacotes-DE5FE9)
![Docker](https://img.shields.io/badge/Docker-opcional-2496ED?logo=docker&logoColor=white)

## Funcionalidades

- Busca de jogos na Steam e na GOG por `id`, nome, desenvolvedora ou distribuidora.
- Lista dos jogos gratuitos no momento na Epic Games Store.
- Filtros combináveis (AND) e com correspondência parcial, sem diferenciar maiúsculas de minúsculas.
- Retorno padronizado nas duas lojas, em reais (BRL).
- Todas as rotas protegidas por API key no header `X-API-Key`.
- Comando para gerar a API key e salvá-la no `.env`.
- Execução via Docker Compose, que gera a chave automaticamente na primeira subida.

## Requisitos

| Ferramenta | Versão | Uso |
| --- | --- | --- |
| Python | 3.12 ou superior | execução local |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | qualquer recente | instalação das dependências |
| Docker + Docker Compose | qualquer recente | execução em container (opcional) |

Funciona em Linux, macOS e Windows.

## Como iniciar

### Com Docker (recomendado)

O arquivo `.env` precisa existir antes de subir, senão o Docker cria uma pasta com esse nome. Crie-o conforme o seu sistema:

| Sistema | Comando |
| --- | --- |
| Linux / macOS | `touch .env` |
| Windows (PowerShell) | `New-Item .env -ItemType File` |
| Windows (CMD) | `type nul > .env` |

Depois, em qualquer sistema:

```bash
docker compose up -d --build
```

O container executa `generate_api_key.py` antes de iniciar a API. Se o `.env` já tiver uma `API_KEY`, ela é mantida; caso contrário, uma nova é gerada, impressa nos logs (`docker compose logs api`) e salva no `.env`.

A API fica em `http://localhost:8000`. Para mudar a porta, defina `APP_PORT` no `.env`.

### Localmente

1. [Instale o uv](https://docs.astral.sh/uv/getting-started/installation/) (Linux, macOS e Windows).
2. Instale as dependências e gere a chave:

```bash
uv sync
uv run python generate_api_key.py   # gera a API_KEY no .env (se ainda não existir)
```

3. Inicie a API (disponível em `http://127.0.0.1:8000`):

```bash
uv run fastapi dev main.py
```

Usar `uv run` evita ativar o ambiente virtual manualmente e funciona igual em Linux, macOS e Windows. Se preferir ativá-lo:

| Sistema | Ativação |
| --- | --- |
| Linux / macOS | `source .venv/bin/activate` |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (CMD) | `.venv\Scripts\activate.bat` |

> [!NOTE]
> A API lê o `.env` apenas ao iniciar. Reinicie o servidor depois de gerar uma nova chave.

### Variáveis de ambiente

| Variável | Descrição | Padrão |
| --- | --- | --- |
| `API_KEY` | Chave exigida no header `X-API-Key`. | gerada por `generate_api_key.py` |
| `APP_PORT` | Porta exposta pelo Docker Compose. | `8000` |

Se `API_KEY` estiver ausente ou com o valor `your_api_key_here`, a API responde `500`.

## Autenticação

Envie a chave em todas as requisições:

```bash
curl -H "X-API-Key: <sua-chave>" "http://localhost:8000/steam/buscar?id=620"
```

| Status | Significado |
| --- | --- |
| `401` | Chave ausente ou inválida. |
| `500` | `API_KEY` não configurada no servidor. |

## Rotas

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/` | Rota de teste (`{"Hello": "World"}`). |
| `GET` | `/items/{item_id}` | Rota de exemplo; aceita o parâmetro opcional `q`. |
| `GET` | `/steam/buscar` | Busca jogos na Steam. |
| `GET` | `/gog/buscar` | Busca jogos na GOG. |
| `GET` | `/epic/gratuitos` | Lista os jogos gratuitos agora na Epic Games Store. |

A documentação interativa está em `/docs` (Swagger) e `/redoc`.

### Parâmetros de `/steam/buscar` e `/gog/buscar`

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `id` | inteiro | ID do jogo na loja. |
| `name` | texto | Nome (ou parte dele). |
| `developer` | texto | Filtra pela desenvolvedora. |
| `publisher` | texto | Filtra pela distribuidora. |

É obrigatório informar `id` ou `name`; sem nenhum dos dois a resposta é `400`. `developer` e `publisher` apenas refinam o resultado. Buscas por `name` retornam no máximo 10 jogos na GOG.

```bash
curl -H "X-API-Key: <sua-chave>" \
  "http://localhost:8000/gog/buscar?name=witcher&developer=cd%20projekt"
```

### Formato da resposta

Lista de jogos com os campos:

```json
[
  {
    "id": 620,
    "url": "https://store.steampowered.com/app/620",
    "nome": "Portal 2",
    "preco": "R$ 33,99",
    "imagens": ["https://..."],
    "videos": ["https://..."],
    "score": 95,
    "plataformas": ["Windows", "Linux"],
    "requisitos_minimos": "Sistema Operativo: Windows 7 ...",
    "data_lancamento": "2011-04-18",
    "idiomas": ["Inglês", "Português (Brasil)"],
    "generos": ["Ação", "Aventura"],
    "descricao": "...",
    "desenvolvedoras": ["Valve"],
    "distribuidoras": ["Valve"]
  }
]
```

| Campo | Steam | GOG |
| --- | --- | --- |
| `url` | página do jogo na loja | página do jogo na loja, ou `null` se o catálogo não fornecer o slug |
| `preco` | preço final, ou `"Gratuito"` | preço final em BRL |
| `imagens` | capa e screenshots | capa e screenshots |
| `videos` | links HLS (`.m3u8`) | embeds do YouTube |
| `score` | nota do Metacritic | avaliação dos usuários, de 0 a 100 |
| `data_lancamento` | `AAAA-MM-DD` (texto original se não reconhecido) | `AAAA-MM-DD` |
| `idiomas` | nomes em português | nomes em inglês |
| `generos` | gêneros informados pela loja | gêneros informados pela loja |

> [!NOTE]
> Na GOG, `descricao` e `requisitos_minimos` vêm em inglês. Jogos que não aparecem no catálogo da GOG podem ter `preco`, `imagens`, `score` e `plataformas` vazios.

### Rota `/epic/gratuitos`

Não recebe parâmetros. Retorna os jogos com 100% de desconto no momento (preços em BRL), no mesmo formato acima, mais os campos `inicio_promocao` e `fim_promocao` (datas ISO em UTC). Também inclui `url` da página na loja.

> [!NOTE]
> A Epic não oferece API pública de busca, então só existe a lista de gratuitos. Nela, `videos`, `score`, `plataformas`, `requisitos_minimos` e `idiomas` vêm vazios ou `null`.

## Estrutura do projeto

```text
.
├── main.py                # app FastAPI e registro das rotas
├── auth.py                # validação da API key
├── generate_api_key.py    # gera e salva a API_KEY no .env
├── routes/
│   ├── steam.py           # rota /steam/buscar
│   ├── gog.py             # rota /gog/buscar
│   └── epic.py            # rota /epic/gratuitos
├── scrappers/
│   ├── steam.py           # integração com a Steam
│   ├── gog_game.py        # integração com a GOG
│   └── epic_games.py      # integração com a Epic Games
├── tests/                 # testes com HTTP mockado
├── Dockerfile
└── docker-compose.yml
```

## Testes

Os testes ficam em `tests/` e usam respostas HTTP mockadas (biblioteca `responses`), sem acessar a Steam nem a GOG.

```bash
uv sync --group dev
uv run pytest
```

## Como contribuir

1. Faça um fork e crie uma branch: `git checkout -b feature/minha-melhoria`.
2. Instale as dependências com `uv sync` e rode a API com `uv run fastapi dev main.py`.
3. Para adicionar uma nova loja, crie o scraper em `scrappers/`, a rota em `routes/` e registre o router em `main.py`, mantendo o [formato de resposta](#formato-da-resposta) e os parâmetros `id`, `name`, `developer` e `publisher`.
4. Teste a rota nova (com e sem a API key) e adicione testes em `tests/`, com as chamadas externas mockadas.
5. Nunca versione o `.env` nem chaves reais.
6. Faça commits pequenos e descritivos e abra um Pull Request explicando o que mudou e por quê.
