"""Tests for the search_jobs tool."""

import json

import pytest

from tools.search_jobs import (
    _date_filter_to_time_range,
    _extract_source,
    _mock_results,
    _parse_title_company,
)


class TestDateFilterToTimeRange:
    def test_day(self):
        assert _date_filter_to_time_range("day") == "day"

    def test_week(self):
        assert _date_filter_to_time_range("week") == "week"

    def test_month(self):
        assert _date_filter_to_time_range("month") == "month"

    def test_3days_maps_to_week(self):
        assert _date_filter_to_time_range("3days") == "week"

    def test_empty(self):
        assert _date_filter_to_time_range("") == ""

    def test_case_insensitive(self):
        assert _date_filter_to_time_range("DAY") == "day"

    def test_unknown(self):
        assert _date_filter_to_time_range("year") == ""


class TestParseTitleCompany:
    def test_dash_separator(self):
        title, company = _parse_title_company("Senior Engineer - Google")
        assert title == "Senior Engineer"
        assert company == "Google"

    def test_at_separator(self):
        title, company = _parse_title_company("Backend Developer at Meta")
        assert title == "Backend Developer"
        assert company == "Meta"

    def test_pipe_separator(self):
        title, company = _parse_title_company("Data Scientist | Amazon")
        assert title == "Data Scientist"
        assert company == "Amazon"

    def test_is_hiring_pattern(self):
        title, company = _parse_title_company("Netflix is hiring Senior Engineer")
        assert title == "Senior Engineer"
        assert company == "Netflix"

    def test_no_separator(self):
        title, company = _parse_title_company("Software Engineer")
        assert title == "Software Engineer"
        assert company == ""


class TestExtractSource:
    def test_linkedin(self):
        assert _extract_source("https://www.linkedin.com/jobs/view/123") == "LinkedIn"

    def test_indeed(self):
        assert _extract_source("https://indeed.com/viewjob?jk=abc") == "Indeed"

    def test_unknown_domain(self):
        assert _extract_source("https://customjobs.example.com/123") == "customjobs.example.com"

    def test_empty_url(self):
        assert _extract_source("") == "Unknown"


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
