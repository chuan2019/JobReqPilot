"""Tests for the search_jobs tool."""

import json

import httpx
import pytest
import respx

from tools.search_jobs import _date_filter_to_chip, _extract_apply_link, _mock_results


class TestDateFilterToChip:
    def test_day(self):
        assert _date_filter_to_chip("day") == "date_posted:today"

    def test_week(self):
        assert _date_filter_to_chip("week") == "date_posted:week"

    def test_month(self):
        assert _date_filter_to_chip("month") == "date_posted:month"

    def test_3days(self):
        assert _date_filter_to_chip("3days") == "date_posted:3days"

    def test_empty(self):
        assert _date_filter_to_chip("") == ""

    def test_case_insensitive(self):
        assert _date_filter_to_chip("DAY") == "date_posted:today"

    def test_unknown(self):
        assert _date_filter_to_chip("year") == ""


class TestExtractApplyLink:
    def test_with_apply_options(self):
        item = {"apply_options": [{"link": "https://example.com/apply"}]}
        assert _extract_apply_link(item) == "https://example.com/apply"

    def test_with_related_links(self):
        item = {"related_links": [{"link": "https://example.com/related"}]}
        assert _extract_apply_link(item) == "https://example.com/related"

    def test_no_links(self):
        assert _extract_apply_link({}) == ""

    def test_apply_options_preferred(self):
        item = {
            "apply_options": [{"link": "https://apply.com"}],
            "related_links": [{"link": "https://related.com"}],
        }
        assert _extract_apply_link(item) == "https://apply.com"


class TestMockResults:
    def test_returns_list(self):
        results = json.loads(_mock_results("test query", 10))
        assert isinstance(results, list)
        assert len(results) > 0

    def test_job_structure(self):
        results = json.loads(_mock_results("test", 10))
        job = results[0]
        assert "title" in job
        assert "company" in job
        assert "url" in job
        assert "snippet" in job
        assert "date_posted" in job
        assert "source" in job

    def test_max_results(self):
        results = json.loads(_mock_results("test", 1))
        assert len(results) == 1

    def test_query_in_snippet(self):
        results = json.loads(_mock_results("Python developer", 10))
        assert "Python developer" in results[0]["snippet"]
