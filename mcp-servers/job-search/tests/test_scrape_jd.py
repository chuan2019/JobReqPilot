"""Tests for the scrape_jd tool."""

import json

import httpx
import pytest
import respx

from tools.scrape_jd import _clean_text, _extract_jd_text, _scrape_single

SAMPLE_HTML = """
<html>
<head><title>Job Posting</title></head>
<body>
    <nav>Navigation stuff</nav>
    <div class="job-description">
        <h2>About the Role</h2>
        <p>We are looking for a Senior Software Engineer to join our team.</p>
        <h3>Requirements</h3>
        <ul>
            <li>5+ years of Python experience</li>
            <li>Experience with FastAPI or Django</li>
            <li>Strong understanding of distributed systems</li>
        </ul>
        <h3>Nice to have</h3>
        <ul>
            <li>Kubernetes experience</li>
            <li>AWS or GCP certification</li>
        </ul>
    </div>
    <footer>Footer stuff</footer>
</body>
</html>
"""

MINIMAL_HTML = """
<html><body><p>Short page.</p></body></html>
"""


class TestExtractJdText:
    def test_extracts_from_job_description_class(self):
        text = _extract_jd_text(SAMPLE_HTML)
        assert "Senior Software Engineer" in text
        assert "5+ years of Python" in text
        assert "Kubernetes experience" in text

    def test_excludes_nav_and_footer(self):
        text = _extract_jd_text(SAMPLE_HTML)
        assert "Navigation stuff" not in text
        assert "Footer stuff" not in text

    def test_short_page_returns_empty(self):
        text = _extract_jd_text(MINIMAL_HTML)
        assert text == ""

    def test_empty_html(self):
        text = _extract_jd_text("")
        assert text == ""


class TestCleanText:
    def test_collapses_blank_lines(self):
        result = _clean_text("hello\n\n\n\nworld")
        assert result == "hello\nworld"

    def test_strips_whitespace(self):
        result = _clean_text("  hello  \n  world  ")
        assert result == "hello\nworld"

    def test_empty_string(self):
        assert _clean_text("") == ""


class TestScrapeSingle:
    @pytest.mark.asyncio
    async def test_invalid_scheme(self):
        result = await _scrape_single("ftp://example.com/job")
        assert result["error"] == "Invalid URL scheme"
        assert result["jd_text"] == ""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_scrape(self):
        respx.get("https://example.com/job/123").mock(
            return_value=httpx.Response(
                200,
                text=SAMPLE_HTML,
                headers={"content-type": "text/html"},
            )
        )
        result = await _scrape_single("https://example.com/job/123")
        assert result["url"] == "https://example.com/job/123"
        assert "Senior Software Engineer" in result["jd_text"]
        assert "error" not in result or result.get("error") is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_http_error(self):
        respx.get("https://example.com/job/404").mock(
            return_value=httpx.Response(404)
        )
        result = await _scrape_single("https://example.com/job/404")
        assert result["error"]
        assert result["jd_text"] == ""

    @respx.mock
    @pytest.mark.asyncio
    async def test_non_html_content_type(self):
        respx.get("https://example.com/file.pdf").mock(
            return_value=httpx.Response(
                200,
                content=b"binary",
                headers={"content-type": "application/pdf"},
            )
        )
        result = await _scrape_single("https://example.com/file.pdf")
        assert "content-type" in result["error"].lower() or "Unexpected" in result["error"]
