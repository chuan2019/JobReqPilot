"""search_jobs tool — searches job boards via Tavily Search API.

Uses Tavily's web search to find job listings. Returns structured job listings
with title, company, URL, snippet, and date posted.
"""

import json
import os
import re

import httpx

from mcp.server.fastmcp import Context, FastMCP

TAVILY_API_URL = "https://api.tavily.com/search"

# Job board domains to prioritize in search results
JOB_BOARD_DOMAINS = [
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "lever.co",
    "greenhouse.io",
    "workday.com",
    "careers.google.com",
    "jobs.apple.com",
    "ziprecruiter.com",
    "monster.com",
    "dice.com",
    "simplyhired.com",
    "builtin.com",
    "angel.co",
    "wellfound.com",
]


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
            max_results: Maximum number of results to return (default 20, max 20)

        Returns:
            JSON array of job objects with: title, company, url, snippet, date_posted, source
        """
        max_results = min(max_results, 20)
        tavily_key = os.getenv("TAVILY_API_KEY", "")

        if not tavily_key:
            if ctx:
                ctx.warning("TAVILY_API_KEY not set — returning mock results for development")
            return _mock_results(query, max_results)

        # Build the search query with job-related context
        search_query = f"job posting {query}"
        if location:
            search_query += f" {location}"

        time_range = _date_filter_to_time_range(date_filter)

        payload = {
            "query": search_query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_domains": JOB_BOARD_DOMAINS,
        }
        if time_range:
            payload["time_range"] = time_range

        headers = {
            "Authorization": f"Bearer {tavily_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    TAVILY_API_URL, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            error_msg = f"Tavily API request failed: {e}"
            if ctx:
                ctx.error(error_msg)
            return json.dumps({"error": error_msg, "jobs": []})

        jobs = []
        for item in data.get("results", []):
            title, company = _parse_title_company(item.get("title", ""))
            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "url": item.get("url", ""),
                    "snippet": (item.get("content", "") or "")[:500],
                    "date_posted": "",
                    "source": _extract_source(item.get("url", "")),
                    "location": location,
                }
            )

        if ctx:
            ctx.info(f"Found {len(jobs)} jobs for query: {query[:80]}")

        return json.dumps(jobs)


def _date_filter_to_time_range(date_filter: str) -> str:
    """Convert a human-readable date filter to Tavily time_range parameter."""
    mapping = {
        "day": "day",
        "3days": "week",
        "week": "week",
        "month": "month",
    }
    return mapping.get(date_filter.lower(), "") if date_filter else ""


def _parse_title_company(raw_title: str) -> tuple[str, str]:
    """Extract job title and company from a search result title.

    Common patterns:
      "Senior Engineer - Company Name"
      "Senior Engineer at Company Name"
      "Senior Engineer | Company Name"
      "Company Name is hiring Senior Engineer"
    """
    # Pattern: "Company is hiring Title"
    hiring_match = re.match(r"^(.+?)\s+is hiring\s+(.+?)(?:\s*[|\-].*)?$", raw_title, re.IGNORECASE)
    if hiring_match:
        return hiring_match.group(2).strip(), hiring_match.group(1).strip()

    # Pattern: "Title at/- /| Company"
    for sep in [" at ", " - ", " | ", " — ", " · "]:
        if sep in raw_title:
            parts = raw_title.split(sep, 1)
            return parts[0].strip(), parts[1].strip()

    return raw_title.strip(), ""


def _extract_source(url: str) -> str:
    """Extract a human-readable source name from a URL."""
    if not url:
        return "Unknown"
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        domain = match.group(1)
        # Map common domains to friendly names
        domain_names = {
            "linkedin.com": "LinkedIn",
            "indeed.com": "Indeed",
            "glassdoor.com": "Glassdoor",
            "lever.co": "Lever",
            "greenhouse.io": "Greenhouse",
            "ziprecruiter.com": "ZipRecruiter",
            "monster.com": "Monster",
            "dice.com": "Dice",
            "builtin.com": "Built In",
            "wellfound.com": "Wellfound",
        }
        for key, name in domain_names.items():
            if key in domain:
                return name
        return domain
    return "Unknown"


def _mock_results(query: str, max_results: int) -> str:
    """Return mock job results for development without a Tavily API key."""
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
