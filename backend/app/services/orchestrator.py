"""MCP Orchestrator — connects to MCP servers and coordinates tool calls.

Acts as the MCP host/client. Connects to the job-search MCP server over SSE,
calls tools in sequence, and handles sampling requests by forwarding them
to the Ollama client.
"""

import json
import logging
import os

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import TextContent

from app.models.search import JobResult, SearchRequest
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class OrchestratorService:
    """Coordinates MCP tool calls for the search flow."""

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama
        self.job_search_url = os.getenv("MCP_JOB_SEARCH_URL", "http://mcp-job-search:8001")

    async def search(self, request: SearchRequest) -> tuple[list[JobResult], str]:
        """Execute the full search flow via MCP tools.

        Returns:
            Tuple of (list of JobResult with jd_text populated, query string used)
        """
        sse_url = f"{self.job_search_url}/sse"

        async with sse_client(sse_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Step 1: Build optimized search query
                query_str = await self._build_query(session, request)

                # Step 2: Search job boards
                raw_jobs = await self._search_jobs(session, query_str, request)

                # Step 3: Scrape full job descriptions
                jobs = await self._scrape_jds(session, raw_jobs)

                return jobs, query_str

    async def _build_query(
        self, session: ClientSession, request: SearchRequest
    ) -> str:
        """Call the build_query MCP tool."""
        try:
            result = await session.call_tool(
                "build_query",
                arguments={
                    "title": request.title,
                    "category": request.category,
                    "keywords": request.keywords,
                },
            )
            text = _extract_text(result)

            # Try to parse as JSON and extract the query field
            try:
                data = json.loads(text)
                if isinstance(data, dict) and "query" in data:
                    return data["query"]
            except json.JSONDecodeError:
                pass

            return text
        except Exception as e:
            logger.error("build_query tool failed: %s", e)
            # Fallback: simple quoted title
            return f'"{request.title}"'

    async def _search_jobs(
        self,
        session: ClientSession,
        query: str,
        request: SearchRequest,
    ) -> list[dict]:
        """Call the search_jobs MCP tool."""
        try:
            result = await session.call_tool(
                "search_jobs",
                arguments={
                    "query": query,
                    "location": request.location,
                    "date_filter": request.date_filter,
                    "max_results": request.max_results,
                },
            )
            text = _extract_text(result)
            data = json.loads(text)

            # Handle error response
            if isinstance(data, dict) and "error" in data:
                logger.warning("search_jobs returned error: %s", data["error"])
                return data.get("jobs", [])

            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("search_jobs tool failed: %s", e)
            return []

    async def _scrape_jds(
        self, session: ClientSession, raw_jobs: list[dict]
    ) -> list[JobResult]:
        """Call the scrape_jd MCP tool and merge JD text into job results."""
        urls = [j.get("url", "") for j in raw_jobs if j.get("url")]

        jd_map: dict[str, str] = {}
        if urls:
            try:
                result = await session.call_tool(
                    "scrape_jd",
                    arguments={"urls": urls},
                )
                text = _extract_text(result)
                scraped = json.loads(text)
                for item in scraped:
                    if item.get("jd_text"):
                        jd_map[item["url"]] = item["jd_text"]
            except Exception as e:
                logger.warning("scrape_jd tool failed: %s — using snippets as fallback", e)

        # Build JobResult list, merging in scraped JD text
        jobs = []
        for raw in raw_jobs:
            url = raw.get("url", "")
            jobs.append(
                JobResult(
                    title=raw.get("title", ""),
                    company=raw.get("company", ""),
                    url=url,
                    snippet=raw.get("snippet", ""),
                    jd_text=jd_map.get(url, ""),
                    date_posted=raw.get("date_posted", ""),
                    source=raw.get("source", ""),
                    location=raw.get("location", ""),
                )
            )
        return jobs


def _extract_text(result) -> str:
    """Extract text content from an MCP tool result."""
    if hasattr(result, "content"):
        for item in result.content:
            if isinstance(item, TextContent):
                return item.text
            if hasattr(item, "text"):
                return item.text
    return str(result)
