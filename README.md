# Medical Diagnostics Support Application

Retrieval-augmented Q&A over clinical reference documents. Upload PDFs or text files, which are chunked,
embedded with OpenAI and stored in a persistent Chroma vector store. Then ask questions whose answers
are grounded in those documents, with sources cited.

| Part       | Stack                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| `backend/` | FastAPI · LangChain · Chroma · OpenAI · optional S3 archival · **uv** |
| `frontend/`| React 19 · TypeScript · Vite, served by nginx in production            |
| Infra      | Dockerfiles per service · Docker Compose · GitHub Actions CI/CD → GHCR |

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # app factory: CORS, routers, lifespan
│   │   ├── core/                   # config (pydantic-settings), logging
│   │   ├── api/
│   │   │   ├── deps.py             # dependency injection (services, settings)
│   │   │   └── v1/routes/          # health, documents, query
│   │   ├── schemas/                # request/response models
│   │   └── services/               # document_processor, vector_store, rag_service, storage_service
│   ├── tests/                      # pytest; fakes for vector store + LLM (no API key needed)
│   ├── pyproject.toml / uv.lock
│   └── Dockerfile
├── frontend/
│   ├── src/{api,components,test}/
│   ├── nginx.conf.template         # serves SPA, proxies /api -> backend
│   └── Dockerfile
├── data/Diabetes.pdf               # sample document
├── docker-compose.yml
├── .env.example
└── .github/workflows/{ci,cd}.yml
```

## API

All routes are under `/api/v1`. Interactive docs are at `/api/v1/docs`.

| Method | Path         | Description                                                    |
| ------ | ------------ | -------------------------------------------------------------- |
| GET    | `/health`    | Liveness check                                                 |
| POST   | `/documents` | Multipart `file` (.pdf/.txt). Chunks, indexes, optionally archives to S3 |
| POST   | `/query`     | `{ "question": str, "history": [{role, content}] }` → `{ answer, sources }` |

## Configuration

```bash
cp .env.example .env   # then set OPENAI_API_KEY (and optional S3 settings)
```

The backend reads `.env` from the repo root (or `backend/`). Legacy variable names from the original
Flask app (`AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `AWS_BUCKET_NAME`) are still accepted.

## Run with Docker Compose

```bash
docker compose up --build
```

- App: http://localhost:8080
- API docs: http://localhost:8000/api/v1/docs

The vector store is kept in the `vector_db` named volume. Run `docker compose down -v` to wipe it.

## Local development (uv + Vite)

Prerequisites: [uv](https://docs.astral.sh/uv/) and Node 22 or later.

```bash
# Backend: uv installs Python 3.12 and all deps into backend/.venv
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Frontend (second terminal): proxies /api to localhost:8000
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Common tasks:

```bash
cd backend
uv add <package>                 # add a dependency (updates pyproject + uv.lock)
uv run pytest                    # tests
uv run ruff check . && uv run ruff format .

cd frontend
npm test && npm run build
```

## CI/CD (GitHub Actions)

- **CI** (`.github/workflows/ci.yml`) runs on every pull request:
  - backend: `uv sync --locked`, ruff lint and format check, pytest
  - frontend: `npm ci`, typecheck, vitest, production build
  - docker: `docker compose build`, starts the stack, smoke-tests `/` and `/api/v1/health` through nginx
- **CD** (`.github/workflows/cd.yml`) runs on pushes to `main` and on `v*.*.*` tags. It reruns CI, then
  builds multi-arch (amd64/arm64) images and pushes them to GitHub Container Registry:
  - `ghcr.io/<owner>/<repo>-backend`
  - `ghcr.io/<owner>/<repo>-frontend`
  - tags: branch, semver, `sha-…`, and `latest` on `main`

  No extra secrets are needed. It uses the built-in `GITHUB_TOKEN`. A deploy job is left as a stub
  at the end of `cd.yml` for your target (SSH + compose, ECS, Kubernetes, …).
- **Dependabot** (`.github/dependabot.yml`) opens weekly update PRs for uv, npm, Docker base images and actions.

To run the published images, use `BACKEND_IMAGE=ghcr.io/... FRONTEND_IMAGE=ghcr.io/... docker compose up -d --no-build`.

## Changes from the original Flask app

- Flask → FastAPI, split into layers (routes / schemas / services / dependency injection).
- conda + `requirements.txt` → uv with `pyproject.toml` and a lockfile.
- LangChain 0.0.267 / openai 0.28 → current `langchain-openai` / `langchain-chroma`. The default model is
  `gpt-4o-mini` (configurable), since `gpt-3.5-turbo` is legacy.
- Chat history is now sent by the client per request, instead of one global server-side memory
  shared by every user.
- S3 archival is optional, and missing configuration returns clear errors (for example 503 when there is no OpenAI key).
- The old `vector_db/` was not migrated, because it was built by chromadb 0.4. Re-upload `data/Diabetes.pdf` to rebuild it.
