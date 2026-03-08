# JobReqPilot — Architecture Design

## Table of Contents
1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component Architecture](#3-component-architecture)
4. [Search Flow](#4-search-flow)
5. [Summarize Flow](#5-summarize-flow)
6. [Semantic Scoring Design](#6-semantic-scoring-design)
7. [Project Directory Structure](#7-project-directory-structure)
8. [Docker Compose Deployment](#8-docker-compose-deployment)
9. [Key Technology Decisions](#9-key-technology-decisions)

---

## 1. System Overview

```mermaid
C4Context
    title System Context — JobReqPilot

    Person(user, "Job Seeker", "Searches job listings and\nanalyzes requirements")

    System(jobreqpilot, "JobReqPilot", "Web application that uses MCP agents\nto search and summarize job postings")

    System_Ext(internet, "Internet / Job Boards", "LinkedIn, Indeed, Google Jobs,\nGlassdoor, etc.")
    System(ollama, "Ollama", "Locally hosted LLM server\n(text generation & embeddings)")

    Rel(user, jobreqpilot, "Uses", "HTTP (local)")
    Rel(jobreqpilot, internet, "Searches via MCP tools", "HTTP")
    Rel(jobreqpilot, ollama, "Calls for reasoning & embeddings", "HTTP (local)")
```

---

## 2. High-Level Architecture

```mermaid
flowchart TB
    subgraph FE["Frontend (React/TypeScript)"]
        UI["Search Form\n(title, category, keywords, date)"]
        ResultTable["Job Results Table\n(sortable by match score)"]
        SummaryPanel["Requirements Summary Panel"]
    end

    subgraph BE["Backend (FastAPI)"]
        API["REST API Layer\n/search  /summarize"]
        Orchestrator["Agent Orchestrator\n(MCP Client)"]
        ScoreEngine["Semantic Scoring Engine\n(cosine similarity on embeddings)"]
        Cache["Result Cache\n(Redis / in-memory)"]
    end

    subgraph MCP["MCP Server Layer"]
        SearchAgent["Job Search Agent\n(MCP Server)"]
        SummarizeAgent["Summarize Agent\n(MCP Server)"]
    end

    subgraph Tools["MCP Tools"]
        WebSearch["web_search tool"]
        Scraper["page_scrape tool"]
        Embedder["embed_text tool"]
    end

    subgraph External["External Services"]
        JobBoards["Job Boards\n(LinkedIn, Indeed, Google Jobs)"]
    end

    subgraph Ollama["Ollama (local Docker service)"]
        OllamaAPI["Ollama REST API\n:11434"]
        LLMModel["LLM Model\n(e.g. qwen2.5, mistral)"]
        EmbedModel["Embedding Model\n(e.g. nomic-embed-text)"]
        OllamaAPI --> LLMModel
        OllamaAPI --> EmbedModel
    end

    UI -->|POST /search| API
    ResultTable -->|POST /summarize| API
    API --> Orchestrator
    Orchestrator --> SearchAgent
    Orchestrator --> SummarizeAgent
    SearchAgent --> WebSearch
    SearchAgent --> Scraper
    SummarizeAgent --> Embedder
    WebSearch --> JobBoards
    Scraper --> JobBoards
    Embedder --> OllamaAPI
    SummarizeAgent --> OllamaAPI
    ScoreEngine --> OllamaAPI
    Orchestrator --> ScoreEngine
    ScoreEngine --> Cache
    Cache --> API
```

---

## 3. Component Architecture

```mermaid
flowchart LR
    subgraph FE["React Frontend"]
        direction TB
        SearchForm["SearchForm\nComponent"]
        JobList["JobList\nComponent"]
        JobCard["JobCard\nComponent"]
        SummaryView["SummaryView\nComponent"]
        Store["Zustand / React Query\nState & Cache"]
        SearchForm --> Store
        Store --> JobList
        JobList --> JobCard
        Store --> SummaryView
    end

    subgraph BE["FastAPI Backend"]
        direction TB
        Router["/api/v1 Router"]
        SearchEndpoint["POST /search"]
        SummarizeEndpoint["POST /summarize"]
        JobModel["Pydantic Models\nSearchRequest / JobResult"]
        OrchestratorSvc["OrchestratorService"]
        ScorerSvc["SemanticScorerService"]
        Router --> SearchEndpoint
        Router --> SummarizeEndpoint
        SearchEndpoint --> OrchestratorSvc
        SummarizeEndpoint --> OrchestratorSvc
        OrchestratorSvc --> ScorerSvc
    end

    subgraph MCP_Servers["MCP Servers (stdio / SSE)"]
        direction TB
        JobSearchServer["job-search-server\n• build_query()\n• search_jobs()\n• scrape_jd()"]
        SummarizeServer["summarize-server\n• aggregate_jds()\n• extract_requirements()\n• rank_requirements()"]
    end

    FE -->|HTTP/JSON| BE
    OrchestratorSvc -->|MCP protocol| JobSearchServer
    OrchestratorSvc -->|MCP protocol| SummarizeServer
```

---

## 4. Search Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant API as FastAPI
    participant Orch as Orchestrator
    participant SearchMCP as Job Search MCP Server
    participant Ollama as Ollama (local)
    participant Web as Job Boards

    User->>UI: Fill form & click Search
    UI->>API: POST /api/v1/search\n{title, category, keywords, date_range}
    API->>Orch: search(request)
    Orch->>SearchMCP: call tool: build_query(inputs)
    SearchMCP->>Ollama: Generate optimized boolean search query
    Ollama-->>SearchMCP: query string
    SearchMCP-->>Orch: structured query
    loop For each job board (LinkedIn, Indeed, Google Jobs)
        Orch->>SearchMCP: call tool: search_jobs(query, board, date_filter)
        SearchMCP->>Web: HTTP search request
        Web-->>SearchMCP: raw results (title, url, snippet)
        SearchMCP-->>Orch: job list chunk
    end
    Orch->>SearchMCP: call tool: scrape_jd(urls[0..100])
    SearchMCP->>Web: Fetch full JD pages
    Web-->>SearchMCP: raw HTML / text
    SearchMCP-->>Orch: parsed JD texts
    Orch->>Ollama: embed(user_query) via nomic-embed-text
    Orch->>Ollama: embed(each JD text) via nomic-embed-text
    Note over Orch: cosine_similarity(query_vec, jd_vec)\n→ match_score ∈ [0,1]
    Orch-->>API: top-100 jobs sorted by score
    API-->>UI: JSON job list
    UI-->>User: Render job table
```

---

## 5. Summarize Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant API as FastAPI
    participant Orch as Orchestrator
    participant SumMCP as Summarize MCP Server
    participant Ollama as Ollama (local)

    User->>UI: Click "Summarize Requirements"
    UI->>API: POST /api/v1/summarize\n{job_ids[] from current results}
    API->>Orch: summarize(job_ids)
    Orch->>SumMCP: call tool: aggregate_jds(jd_texts[])
    Note over SumMCP: Chunk & deduplicate JD content
    SumMCP->>Ollama: Extract structured requirements\nfrom each chunk
    Ollama-->>SumMCP: per-chunk requirements JSON
    SumMCP->>Ollama: Merge & rank requirements\nacross all chunks
    Ollama-->>SumMCP: final ranked requirements
    SumMCP-->>Orch: RequirementsSummary
    Orch-->>API: summary payload
    API-->>UI: JSON summary
    UI-->>User: Render summary panel
```

---

## 6. Semantic Scoring Design

Match scores use **embedding-based cosine similarity**, the industry-standard approach used by LinkedIn, Indeed, and modern ATS systems.

```mermaid
flowchart LR
    subgraph Input
        Q["User Query\n= title + category\n+ keywords"]
        JD["Job Description\nfull text"]
    end

    subgraph Embedding["Embedding Layer (Ollama / nomic-embed-text)"]
        QEmb["embed(query)\n→ vector ℝ⁷⁶⁸"]
        JDEmb["embed(jd)\n→ vector ℝ⁷⁶⁸"]
    end

    subgraph Score["Scoring"]
        Cosine["cosine_similarity\n= (Q·JD) / (‖Q‖·‖JD‖)\n∈ [-1, 1] → normalize → [0, 1]"]
        Boost["Optional boosts:\n+0.05 if title exact match\n+0.03 per keyword hit\n+0.02 recency bonus"]
        Final["final_score = clamp(cosine + boosts, 0, 1)"]
    end

    Q --> QEmb
    JD --> JDEmb
    QEmb --> Cosine
    JDEmb --> Cosine
    Cosine --> Boost
    Boost --> Final
```

### Scoring Formula

```
# embed() calls Ollama's nomic-embed-text model at http://ollama:11434/api/embeddings
base_score  = cosine_similarity(embed(query), embed(jd))   # ∈ [0, 1]
title_boost = 0.05 if job_title contains query_title (case-insensitive)
kw_boost    = 0.03 × min(matched_keywords / total_keywords, 1.0)
date_boost  = 0.02 if posted within date_range else 0

final_score = clamp(base_score + title_boost + kw_boost + date_boost, 0.0, 1.0)
```

---

## 7. Project Directory Structure

```
JobReqPilot/
├── frontend/                        # React + TypeScript (Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchForm.tsx       # Title, category, keywords, date inputs
│   │   │   ├── JobList.tsx          # Sortable results table
│   │   │   ├── JobCard.tsx          # Individual job result row
│   │   │   └── SummaryView.tsx      # Requirements summary panel
│   │   ├── api/                     # Axios/fetch wrappers
│   │   │   ├── search.ts
│   │   │   └── summarize.ts
│   │   ├── store/                   # Zustand global state
│   │   │   └── jobStore.ts
│   │   └── types/                   # Shared TypeScript types
│   │       └── index.ts
│   ├── index.html
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── package.json
│
├── backend/                         # FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── search.py        # POST /api/v1/search
│   │   │       └── summarize.py     # POST /api/v1/summarize
│   │   ├── models/                  # Pydantic schemas
│   │   │   ├── search.py            # SearchRequest, JobResult
│   │   │   └── summarize.py         # SummarizeRequest, RequirementsSummary
│   │   ├── services/
│   │   │   ├── orchestrator.py      # MCP client, agent coordination
│   │   │   └── scorer.py            # Embedding + cosine similarity
│   │   └── main.py                  # FastAPI app entry point
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example                 # OLLAMA_BASE_URL, SERPAPI_KEY, etc.
│
├── mcp-servers/
│   ├── job-search/                  # MCP Server 1 — Job Search
│   │   ├── server.py                # MCP server entry point
│   │   ├── Dockerfile
│   │   └── tools/
│   │       ├── build_query.py       # LLM-powered boolean query builder
│   │       ├── search_jobs.py       # Multi-board job search
│   │       └── scrape_jd.py         # JD page scraper & parser
│   └── summarize/                   # MCP Server 2 — Summarization
│       ├── server.py
│       ├── Dockerfile
│       └── tools/
│           ├── aggregate_jds.py     # Chunk & deduplicate JD content
│           └── extract_requirements.py  # LLM-powered requirement extraction
│
├── docker-compose.yml               # Orchestrates all services + Ollama
├── docker-compose.override.yml      # Dev overrides (hot-reload, port bindings)
├── .env.example                     # Top-level env template
└── docs/
    └── ARCHITECTURE.md
```

---

## 8. Docker Compose Deployment

All services run as containers in a shared Docker Compose network (`jobreqpilot_net`). Ollama is included as a service so no external API keys or cloud LLM access are required.

```mermaid
flowchart TB
    subgraph DC["docker-compose.yml"]
        FE_C["frontend\n:3000\n(Vite / Nginx)"]
        BE_C["backend\n:8000\n(FastAPI + Uvicorn)"]
        JS_C["mcp-job-search\n:8001\n(MCP SSE Server)"]
        SUM_C["mcp-summarize\n:8002\n(MCP SSE Server)"]
        REDIS["redis\n:6379"]
        OLL["ollama\n:11434\n(GPU-enabled if available)"]
    end

    FE_C -->|HTTP :8000| BE_C
    BE_C -->|MCP SSE :8001| JS_C
    BE_C -->|MCP SSE :8002| SUM_C
    BE_C -->|cache| REDIS
    JS_C -->|/api/generate\n/api/embeddings| OLL
    SUM_C -->|/api/generate\n/api/embeddings| OLL
    BE_C -->|/api/embeddings| OLL
```

### Service Summary

| Service | Image | Ports | Purpose |
|---|---|---|---|
| `frontend` | `jobreqpilot/frontend` | `3000` | React UI (Nginx in prod, Vite HMR in dev) |
| `backend` | `jobreqpilot/backend` | `8000` | FastAPI REST API + orchestrator |
| `mcp-job-search` | `jobreqpilot/mcp-job-search` | `8001` | Job Search MCP Server (SSE transport) |
| `mcp-summarize` | `jobreqpilot/mcp-summarize` | `8002` | Summarize MCP Server (SSE transport) |
| `redis` | `redis:7-alpine` | `6379` | Result & embedding cache |
| `ollama` | `ollama/ollama` | `11434` | Local LLM inference server |

### Environment Variables (`.env`)

```dotenv
# Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_LLM_MODEL=qwen2.5:14b          # or mistral, llama3.2, etc.
OLLAMA_EMBED_MODEL=nomic-embed-text

# External
SERPAPI_KEY=<your-key>

# Redis
REDIS_URL=redis://redis:6379/0
```

### Ollama Model Pull (first run)

```bash
# Pull required models on first start (runs inside the ollama container)
docker compose run --rm ollama ollama pull qwen2.5:14b
docker compose run --rm ollama ollama pull nomic-embed-text
```

### Dev vs Prod

- **Dev** (`docker compose up`): uses `docker-compose.override.yml` — mounts source dirs as volumes for hot-reload, exposes all ports on localhost.
- **Prod** (`docker compose -f docker-compose.yml up`): no volume mounts, Nginx serves the built React bundle, only port `3000` exposed externally.

---

## 9. Key Technology Decisions

| Concern | Choice | Rationale |
|---|---|---|
| **MCP transport** | SSE (Docker service-to-service) | Services communicate over the internal Docker network; SSE is stateless and horizontally scalable |
| **LLM** | Ollama — `qwen2.5:14b` (default) | Runs fully locally via Docker; no API key required; swappable via `OLLAMA_LLM_MODEL` env var |
| **Embeddings** | Ollama — `nomic-embed-text` (768-dim) | State-of-the-art open-source embedding model; runs locally via the same Ollama container |
| **Scoring** | Cosine similarity on dense embeddings + lightweight heuristic boosts | Industry standard; interpretable; fast at inference time |
| **Frontend state** | React Query (server state) + Zustand (UI state) | React Query handles caching & background refetch; Zustand is minimal |
| **Job board access** | SerpAPI / Bright Data or direct scraping via MCP tool | SerpAPI gives structured results with legal compliance |
| **Backend cache** | Redis (Docker service) | Avoids re-embedding identical queries; TTL-based invalidation; same service in dev and prod |
| **API style** | REST with SSE streaming for long-running searches | Simple to consume from React; streaming gives progressive UX |
| **Deployment** | Docker Compose | Single `docker compose up` starts the full stack including Ollama; no cloud dependencies |
