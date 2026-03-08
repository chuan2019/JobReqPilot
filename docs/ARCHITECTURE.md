# JobReqPilot — Architecture Design

## Table of Contents
1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component Architecture](#3-component-architecture)
4. [Search Flow](#4-search-flow)
5. [Summarize Flow](#5-summarize-flow)
6. [Semantic Scoring Design](#6-semantic-scoring-design)
7. [Project Directory Structure](#7-project-directory-structure)
8. [Key Technology Decisions](#8-key-technology-decisions)

---

## 1. System Overview

```mermaid
C4Context
    title System Context — JobReqPilot

    Person(user, "Job Seeker", "Searches job listings and\nanalyzes requirements")

    System(jobreqpilot, "JobReqPilot", "Web application that uses MCP agents\nto search and summarize job postings")

    System_Ext(internet, "Internet / Job Boards", "LinkedIn, Indeed, Google Jobs,\nGlassdoor, etc.")
    System_Ext(llm, "LLM Provider", "Claude / OpenAI\n(text generation & embeddings)")

    Rel(user, jobreqpilot, "Uses", "HTTPS")
    Rel(jobreqpilot, internet, "Searches via MCP tools", "HTTP")
    Rel(jobreqpilot, llm, "Calls for reasoning & embeddings", "HTTPS")
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
        LLM["LLM API\n(Claude)"]
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
    Embedder --> LLM
    SummarizeAgent --> LLM
    ScoreEngine --> LLM
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
    participant LLM as Claude LLM
    participant Web as Job Boards

    User->>UI: Fill form & click Search
    UI->>API: POST /api/v1/search\n{title, category, keywords, date_range}
    API->>Orch: search(request)
    Orch->>SearchMCP: call tool: build_query(inputs)
    SearchMCP->>LLM: Generate optimized boolean search query
    LLM-->>SearchMCP: query string
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
    Orch->>LLM: embed(user_query)
    Orch->>LLM: embed(each JD text)
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
    participant LLM as Claude LLM

    User->>UI: Click "Summarize Requirements"
    UI->>API: POST /api/v1/summarize\n{job_ids[] from current results}
    API->>Orch: summarize(job_ids)
    Orch->>SumMCP: call tool: aggregate_jds(jd_texts[])
    Note over SumMCP: Chunk & deduplicate JD content
    SumMCP->>LLM: Extract structured requirements\nfrom each chunk
    LLM-->>SumMCP: per-chunk requirements JSON
    SumMCP->>LLM: Merge & rank requirements\nacross all chunks
    LLM-->>SumMCP: final ranked requirements
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

    subgraph Embedding["Embedding Layer (Claude / OpenAI)"]
        QEmb["embed(query)\n→ vector ℝ¹⁵³⁶"]
        JDEmb["embed(jd)\n→ vector ℝ¹⁵³⁶"]
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
│   └── .env.example
│
├── mcp-servers/
│   ├── job-search/                  # MCP Server 1 — Job Search
│   │   ├── server.py                # MCP server entry point
│   │   └── tools/
│   │       ├── build_query.py       # LLM-powered boolean query builder
│   │       ├── search_jobs.py       # Multi-board job search
│   │       └── scrape_jd.py         # JD page scraper & parser
│   └── summarize/                   # MCP Server 2 — Summarization
│       ├── server.py
│       └── tools/
│           ├── aggregate_jds.py     # Chunk & deduplicate JD content
│           └── extract_requirements.py  # LLM-powered requirement extraction
│
├── docker-compose.yml
└── ARCHITECTURE.md
```

---

## 8. Key Technology Decisions

| Concern | Choice | Rationale |
|---|---|---|
| **MCP transport** | stdio (dev) / SSE (prod) | stdio is simple locally; SSE allows horizontal scaling |
| **LLM** | Claude claude-sonnet-4-6 | Best tool-use & long-context support (needed for 100 JDs) |
| **Embeddings** | `text-embedding-3-large` (OpenAI) or Claude embeddings | 1536-dim vectors; best-in-class semantic retrieval accuracy |
| **Scoring** | Cosine similarity on dense embeddings + lightweight heuristic boosts | Industry standard; interpretable; fast at inference time |
| **Frontend state** | React Query (server state) + Zustand (UI state) | React Query handles caching & background refetch; Zustand is minimal |
| **Job board access** | SerpAPI / Bright Data or direct scraping via MCP tool | SerpAPI gives structured results with legal compliance |
| **Backend cache** | Redis (prod) / in-memory dict (dev) | Avoids re-embedding identical queries; TTL-based invalidation |
| **API style** | REST with SSE streaming for long-running searches | Simple to consume from React; streaming gives progressive UX |
