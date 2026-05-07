# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Start all services (dev mode with hot-reload)
```bash
docker compose up
```
The `docker-compose.override.yml` is automatically merged, giving the backend `--reload`, the frontend Vite HMR, and volume-mounted source files.

### Production (no override)
```bash
docker compose -f docker-compose.yml up
```

### Pull LLM models (first run only)
```bash
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text
```

### Run tests
```bash
# Frontend (Vitest)
cd frontend && npm test

# MCP server — job-search
cd mcp-servers/job-search && uv sync --extra dev && uv run pytest tests/ -v

# MCP server — summarize
cd mcp-servers/summarize && uv sync --extra dev && uv run pytest tests/ -v

# Run a single test file
cd mcp-servers/job-search && uv sync --extra dev && uv run pytest tests/test_build_query.py -v
```

### Frontend type-check
```bash
cd frontend && npx tsc --noEmit
```

### Install Python dependencies (per service, using uv)
```bash
cd backend && uv sync --extra dev
cd mcp-servers/job-search && uv sync --extra dev
cd mcp-servers/summarize && uv sync --extra dev
```

## Architecture

JobReqPilot is a multi-service application where a React frontend talks to a FastAPI backend, which in turn orchestrates two MCP servers over SSE transport and a local Ollama instance.

```
Frontend (React/Vite :3000)
  └─> Backend (FastAPI :8000)
        ├─> MCP job-search server (:8001)  — build_query, search_jobs, scrape_jd
        ├─> MCP summarize server (:8002)   — aggregate_jds, extract_requirements
        ├─> Ollama (:11434)                — embeddings + LLM generation
        └─> Redis (:6379)                  — result cache + embedding cache
```

### Backend (`backend/app/`)

The backend is a FastAPI app with a lifespan-managed set of shared services stored on `app.state`:

- **`OrchestratorService`** (`services/orchestrator.py`) — the MCP host/client. Opens SSE connections to the MCP servers and calls their tools in sequence. Search flow: `build_query → search_jobs → scrape_jd`. Summarize flow: `aggregate_jds → extract_requirements`.
- **`ScorerService`** (`services/scorer.py`) — batch-embeds query + all JD texts via Ollama, computes cosine similarity, and applies heuristic boosts (title match +0.05, keyword hits up to +0.03, recency +0.02).
- **`OllamaClient`** (`services/ollama_client.py`) — wraps Ollama's REST API for both embedding batches and LLM generation. The Redis connection is injected into it at startup for embedding cache hits.
- **`CacheService`** (`services/cache.py`) — async Redis client. Keys are `{prefix}:{sha256_hex[:16]}` of the serialized request body. Default TTL is 1 hour.

API routes (`api/v1/`) use `request.app.state` to access services — no dependency injection framework.

### MCP Servers (`mcp-servers/`)

Each MCP server uses `mcp.server.fastmcp.FastMCP` and runs with SSE transport. Tools are registered via `register_tools(server)` functions in a `tools/` package, rather than direct decorators, so they can be tested in isolation.

- **`mcp-servers/job-search/`**: Tools — `build_query` (constructs an optimized Tavily search string), `search_jobs` (calls Tavily API, returns structured job list), `scrape_jd` (batch-fetches URLs and extracts JD text via BeautifulSoup/lxml).
- **`mcp-servers/summarize/`**: Tools — `aggregate_jds` (chunks and deduplicates JD text corpus), `extract_requirements` (calls Ollama LLM to extract structured requirements by category, ranked by frequency).

The MCP summarize server calls Ollama directly (via `OLLAMA_BASE_URL`) for LLM generation; the backend calls Ollama for embeddings only.

### Frontend (`frontend/src/`)

- **State**: Zustand store (`store/jobStore.ts`) tracks selected job URLs (used as IDs) and search parameters.
- **Server state**: TanStack Query mutations (`useMutation`) for search and summarize API calls; no query caching (mutations are fire-and-forget).
- **Types** (`types/index.ts`) mirror the backend Pydantic models exactly — keep them in sync manually when models change.
- **API** (`api/search.ts`, `api/summarize.ts`) — axios with `baseURL: '/api/v1'`. In dev, Vite proxies `/api` to `http://backend:8000` (configured in Vite config). In prod, Nginx handles the proxy.

### Key data flow: `job_ids` in summarize

When the user selects jobs and clicks "Summarize," the frontend sends `job_ids: string[]` which are actually job **URLs**. The backend looks these up in the cached search results to retrieve `jd_text` for each selected job before calling the MCP summarize server.

## Environment

Copy `.env.example` to `.env` before starting. The only required external secret is `TAVILY_API_KEY`. All other services run locally. The `docker-compose.override.yml` does not load `.env` explicitly — variables are read from the shell environment or the `environment:` blocks in `docker-compose.yml`.
