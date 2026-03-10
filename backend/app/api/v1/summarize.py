"""POST /api/v1/summarize — requirements summarization endpoint."""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.summarize import SummarizeRequest, SummarizeResponse
from app.services.cache import CacheService
from app.services.orchestrator import OrchestratorService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(body: SummarizeRequest, request: Request):
    """Summarize requirements from selected job descriptions."""
    cache: CacheService = request.app.state.cache
    orchestrator: OrchestratorService = request.app.state.orchestrator

    # Check cache
    cache_key = CacheService.make_key("summarize", body.model_dump())
    cached = await cache.get(cache_key)
    if cached:
        logger.info("Cache hit for summarize: %s", cache_key)
        cached["cached"] = True
        return SummarizeResponse(**cached)

    # Retrieve cached JD texts for the given job IDs (URLs).
    # Job texts are stored in the search response cache — look them up.
    jd_texts = await _resolve_jd_texts(cache, body.job_ids)

    if not jd_texts:
        raise HTTPException(
            status_code=404,
            detail="No job description texts found for the given job IDs. "
            "Please run a search first so job data is cached.",
        )

    # Execute MCP summarize flow: aggregate_jds → extract_requirements
    summary = await orchestrator.summarize(jd_texts)

    response = SummarizeResponse(
        summary=summary,
        job_count=len(jd_texts),
    )

    # Cache the result
    await cache.set(cache_key, response.model_dump())

    return response


async def _resolve_jd_texts(
    cache: CacheService, job_ids: list[str]
) -> list[str]:
    """Look up JD texts from cached search results.

    Scans all cached search responses to find JD texts matching the
    requested job URLs. Falls back to snippets if jd_text is empty.
    """
    if not cache._redis:
        return []

    jd_texts: list[str] = []
    job_id_set = set(job_ids)

    try:
        # Scan for all search cache keys
        async for key in cache._redis.scan_iter(match="search:*"):
            raw = await cache._redis.get(key)
            if not raw:
                continue

            import json
            data = json.loads(raw)
            for job in data.get("jobs", []):
                url = job.get("url", "")
                if url in job_id_set:
                    text = job.get("jd_text", "") or job.get("snippet", "")
                    if text:
                        jd_texts.append(text)
                    job_id_set.discard(url)

            if not job_id_set:
                break  # Found all requested jobs
    except Exception as e:
        logger.warning("Failed to resolve JD texts from cache: %s", e)

    return jd_texts
