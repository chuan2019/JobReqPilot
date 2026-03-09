"""search_jobs tool — searches job boards via SerpAPI.

Supports Google Jobs as the primary engine. Returns structured job listings
with title, company, URL, snippet, and date posted.
"""

import json
import os

import httpx

from mcp.server.fastmcp import Context, FastMCP

SERPAPI_BASE_URL = "https://serpapi.com/search"


def register_tools(server: FastMCP) -> None:
    @server.tool()
    async def search_jobs(
        query: str,
        location: str = "",
        date_filter: str = "",
        max_results: int = 20,
        ctx: Context = None,
    ) -> str:
        """Search job boards and return structured job listings.

        Args:
            query: Boolean search query string (from build_query tool)
            location: Geographic location filter (e.g. "San Francisco, CA")
            date_filter: Recency filter — "day", "3days", "week", "month", or ""
            max_results: Maximum number of results to return (default 20, max 100)

        Returns:
            JSON array of job objects with: title, company, url, snippet, date_posted, source
        """
        max_results = min(max_results, 100)
        serpapi_key = os.getenv("SERPAPI_KEY", "")

        if not serpapi_key:
            if ctx:
                ctx.warning("SERPAPI_KEY not set — returning mock results for development")
            return _mock_results(query, max_results)

        # Map date_filter to SerpAPI's chips parameter
        date_chip = _date_filter_to_chip(date_filter)

        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": serpapi_key,
            "num": str(max_results),
        }
        if location:
            params["location"] = location
        if date_chip:
            params["chips"] = date_chip

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(SERPAPI_BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            error_msg = f"SerpAPI request failed: {e}"
            if ctx:
                ctx.error(error_msg)
            return json.dumps({"error": error_msg, "jobs": []})

        jobs = []
        for item in data.get("jobs_results", [])[:max_results]:
            jobs.append(
                {
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "url": _extract_apply_link(item),
                    "snippet": item.get("description", "")[:500],
                    "date_posted": item.get("detected_extensions", {}).get(
                        "posted_at", ""
                    ),
                    "source": item.get("via", "Google Jobs"),
                    "location": item.get("location", ""),
                }
            )

        if ctx:
            ctx.info(f"Found {len(jobs)} jobs for query: {query[:80]}")

        return json.dumps(jobs)


def _date_filter_to_chip(date_filter: str) -> str:
    """Convert a human-readable date filter to SerpAPI chips parameter."""
    mapping = {
        "day": "date_posted:today",
        "3days": "date_posted:3days",
        "week": "date_posted:week",
        "month": "date_posted:month",
    }
    return mapping.get(date_filter.lower(), "")


def _extract_apply_link(item: dict) -> str:
    """Extract the best apply link from a SerpAPI job result."""
    apply_options = item.get("apply_options", [])
    if apply_options:
        return apply_options[0].get("link", "")
    related = item.get("related_links", [])
    if related:
        return related[0].get("link", "")
    return ""


def _mock_results(query: str, max_results: int) -> str:
    """Return mock job results for development without a SerpAPI key."""
    mock_jobs = [
        {
            "title": "Senior Software Engineer",
            "company": "TechCorp Inc.",
            "url": "https://example.com/jobs/1",
            "snippet": f"Looking for an experienced engineer. Query matched: {query[:100]}",
            "date_posted": "2 days ago",
            "source": "Mock Data",
            "location": "San Francisco, CA",
        },
        {
            "title": "Backend Developer",
            "company": "StartupXYZ",
            "url": "https://example.com/jobs/2",
            "snippet": "Join our team building scalable microservices with Python and Go.",
            "date_posted": "1 week ago",
            "source": "Mock Data",
            "location": "Remote",
        },
        {
            "title": "Full Stack Engineer",
            "company": "BigCo",
            "url": "https://example.com/jobs/3",
            "snippet": "Full stack role using React, TypeScript, and Python/FastAPI.",
            "date_posted": "3 days ago",
            "source": "Mock Data",
            "location": "New York, NY",
        },
    ]
    return json.dumps(mock_jobs[:max_results])
