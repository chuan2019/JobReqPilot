"""POST /api/v1/search — job search endpoint."""

import logging

from fastapi import APIRouter, Request

from app.models.search import SearchRequest, SearchResponse
from app.services.cache import CacheService
from app.services.orchestrator import OrchestratorService
from app.services.scorer import ScorerService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, request: Request):
    """Search for jobs, score results, and return ranked listings."""
    cache: CacheService = request.app.state.cache
    orchestrator: OrchestratorService = request.app.state.orchestrator
    scorer: ScorerService = request.app.state.scorer

    # Check cache
    cache_key = CacheService.make_key("search", body.model_dump())
    cached = await cache.get(cache_key)
    if cached:
        logger.info("Cache hit for search: %s", cache_key)
        cached["cached"] = True
        return SearchResponse(**cached)

    # Execute MCP search flow: build_query → search_jobs → scrape_jd
    jobs, query_used = await orchestrator.search(body)

    # Score results with embeddings + heuristic boosts
    query_text = f"{body.title} {body.category} {' '.join(body.keywords)}".strip()
    scored_jobs = await scorer.score(
        query_text=query_text,
        jobs=jobs,
        title=body.title,
        keywords=body.keywords,
        date_filter=body.date_filter,
    )

    response = SearchResponse(
        jobs=scored_jobs,
        total=len(scored_jobs),
        query_used=query_used,
    )

    # Cache the result
    await cache.set(cache_key, response.model_dump())

    return response
