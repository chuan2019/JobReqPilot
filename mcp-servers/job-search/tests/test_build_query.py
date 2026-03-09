"""Tests for the build_query tool."""

import json

import pytest

from tools.build_query import _heuristic_query


class TestHeuristicQuery:
    """Test the fallback heuristic query builder."""

    def test_title_only(self):
        result = json.loads(_heuristic_query("Software Engineer", "", []))
        assert '"Software Engineer"' in result["query"]
        assert result["title_variants"] == ["Software Engineer"]
        assert result["excluded_terms"] == []

    def test_title_and_category(self):
        result = json.loads(
            _heuristic_query("Data Scientist", "Machine Learning", [])
        )
        assert '"Data Scientist"' in result["query"]
        assert '"Machine Learning"' in result["query"]
        assert "AND" in result["query"]

    def test_title_and_keywords(self):
        result = json.loads(
            _heuristic_query("Backend Developer", "", ["Python", "FastAPI"])
        )
        assert '"Backend Developer"' in result["query"]
        assert '"Python"' in result["query"]
        assert '"FastAPI"' in result["query"]
        assert "OR" in result["query"]

    def test_all_fields(self):
        result = json.loads(
            _heuristic_query(
                "SRE", "Infrastructure", ["Kubernetes", "Terraform", "AWS"]
            )
        )
        query = result["query"]
        assert '"SRE"' in query
        assert '"Infrastructure"' in query
        assert '"Kubernetes"' in query
        assert "AND" in query
        assert "OR" in query

    def test_returns_valid_json(self):
        result = json.loads(_heuristic_query("Engineer", "", []))
        assert "query" in result
        assert "title_variants" in result
        assert "excluded_terms" in result
