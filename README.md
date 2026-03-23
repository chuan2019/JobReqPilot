# JobReqPilot

AI-powered job search and requirements analysis tool using MCP (Model Context Protocol) agents.

Search job boards, score results with semantic embeddings, and extract consolidated requirements from multiple job descriptions — all running locally with Ollama.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — add your TAVILY_API_KEY (get one at https://tavily.com)

# 2. Start all services
docker compose up

# 3. Pull LLM models (first run only)
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text

# 4. Open the app
open http://localhost:3000
```

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌────────────────────┐
│   Frontend   │───▶│   Backend    │───▶│  MCP Job Search    │
│  React + TS  │    │   FastAPI    │    │  (Tavily + Scrape) │
│  :3000       │    │  :8000       │    │  :8001             │
└──────────────┘    │              │    └────────────────────┘
                    │              │───▶┌────────────────────┐
                    │              │    │  MCP Summarize     │
                    │              │    │  (Aggregate + LLM) │
                    └──────┬───────┘    │  :8002             │
                           │           └────────────────────┘
                    ┌──────┴───────┐
                    │   Ollama     │    ┌──────────────┐
                    │  LLM + Embed │    │    Redis     │
                    │  :11434      │    │    :6379     │
                    └──────────────┘    └──────────────┘
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `frontend` | 3000 | React UI (Nginx in prod, Vite HMR in dev) |
| `backend` | 8000 | FastAPI REST API + orchestrator |
| `mcp-job-search` | 8001 | MCP server: query building, job search (Tavily), JD scraping |
| `mcp-summarize` | 8002 | MCP server: JD aggregation, requirements extraction |
| `ollama` | 11434 | Local LLM inference (text generation + embeddings) |
| `redis` | 6379 | Result cache + embedding cache |

## Features

- **Job Search**: Enter a title, category, and keywords to search across 15+ job boards via Tavily
- **Semantic Scoring**: Jobs are scored using cosine similarity on embeddings (nomic-embed-text) with heuristic boosts
- **Requirements Summarization**: Select jobs and extract consolidated requirements ranked by frequency
- **Local LLM**: All AI processing runs locally via Ollama — no cloud API keys needed (except Tavily for search)
- **Caching**: Search results and embeddings are cached in Redis to avoid redundant API calls

## Development

```bash
# Start in dev mode (hot-reload for backend + frontend)
docker compose up

# Run frontend tests
cd frontend && npm test

# Run MCP server tests
cd mcp-servers/job-search && uv run pytest tests/ -v
cd mcp-servers/summarize && uv run pytest tests/ -v

# Type-check frontend
cd frontend && npx tsc --noEmit
```

### Environment Variables

See [.env.example](.env.example) for all configuration options. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TAVILY_API_KEY` | (required) | API key for Tavily job search |
| `OLLAMA_LLM_MODEL` | `llama3.2` | LLM model for text generation |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Model for embeddings |
| `LOG_LEVEL` | `info` | Logging level (debug, info, warning, error) |
| `LOG_FORMAT` | `text` | Log format (`text` or `json`) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/search` | Search jobs and return scored results |
| `POST` | `/api/v1/summarize` | Extract requirements from selected jobs |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | FastAPI auto-generated API documentation |

## Tech Stack

- **Frontend**: React 19, TypeScript, Vite 7, TanStack Query, Zustand
- **Backend**: FastAPI, Pydantic, httpx, numpy
- **MCP Servers**: Python MCP SDK with SSE transport
- **LLM**: Ollama (llama3.2 + nomic-embed-text)
- **Infrastructure**: Docker Compose, Redis, Nginx

