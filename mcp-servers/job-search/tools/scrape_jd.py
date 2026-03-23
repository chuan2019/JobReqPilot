"""scrape_jd tool — fetches and parses job description pages.

Given a list of URLs, fetches each page concurrently and extracts
the main job description text using BeautifulSoup.
"""

import asyncio
import json
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from mcp.server.fastmcp import Context, FastMCP

# Max concurrent requests to avoid overwhelming targets
MAX_CONCURRENCY = 10
REQUEST_TIMEOUT = 15.0
MAX_JD_LENGTH = 10_000

# Common selectors for job description content, tried in order
JD_SELECTORS = [
    '[class*="job-description"]',
    '[class*="jobDescription"]',
    '[class*="job_description"]',
    '[class*="description"]',
    '[id*="job-description"]',
    '[id*="jobDescription"]',
    "article",
    '[role="main"]',
    "main",
]

# Tags that typically contain noise, not content
NOISE_TAGS = {"script", "style", "nav", "header", "footer", "aside", "form", "iframe"}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def register_tools(server: FastMCP) -> None:
    @server.tool()
    async def scrape_jd(
        urls: list[str],
        ctx: Context = None,
    ) -> str:
        """Scrape job description text from a list of URLs.

        Args:
            urls: List of job posting URLs to scrape (max 100)

        Returns:
            JSON array of objects with: url, jd_text, error (if scraping failed)
        """
        urls = urls[:100]

        semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        results = []

        async def _fetch_one(url: str) -> dict:
            async with semaphore:
                return await _scrape_single(url)

        tasks = [_fetch_one(url) for url in urls]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if not r.get("error"))
        if ctx:
            ctx.info(
                f"Scraped {success_count}/{len(urls)} pages successfully"
            )

        return json.dumps(list(results))


def _is_safe_url(url: str) -> tuple[bool, str]:
    """Validate URL to prevent SSRF attacks against internal services."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "Invalid URL scheme"
    hostname = parsed.hostname or ""
    # Block internal/private hostnames
    blocked = ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google",
               "169.254.169.254")
    if hostname in blocked or hostname.endswith(".internal") or hostname.endswith(".local"):
        return False, "Internal URLs are not allowed"
    # Block private IP ranges
    try:
        import ipaddress
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False, "Private IP addresses are not allowed"
    except ValueError:
        pass  # hostname is not an IP, that's fine
    return True, ""


async def _scrape_single(url: str) -> dict:
    """Fetch and parse a single job posting URL."""
    safe, reason = _is_safe_url(url)
    if not safe:
        return {"url": url, "jd_text": "", "error": reason}

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as e:
        return {"url": url, "jd_text": "", "error": str(e)}

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        return {"url": url, "jd_text": "", "error": f"Unexpected content-type: {content_type}"}

    jd_text = _extract_jd_text(response.text)
    if not jd_text:
        return {"url": url, "jd_text": "", "error": "Could not extract job description"}

    return {"url": url, "jd_text": jd_text[:MAX_JD_LENGTH]}


def _extract_jd_text(html: str) -> str:
    """Extract job description text from HTML using heuristic selectors."""
    soup = BeautifulSoup(html, "lxml")

    # Remove noise tags
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    # Try specific JD selectors first
    for selector in JD_SELECTORS:
        elements = soup.select(selector)
        if elements:
            # Take the largest matching element by text length
            best = max(elements, key=lambda el: len(el.get_text(strip=True)))
            text = best.get_text(separator="\n", strip=True)
            if len(text) > 100:
                return _clean_text(text)

    # Fallback: extract from <body>
    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n", strip=True)
        if len(text) > 100:
            return _clean_text(text)

    return ""


def _clean_text(text: str) -> str:
    """Clean extracted text — collapse whitespace, remove empty lines."""
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            lines.append(line)
    return "\n".join(lines)
