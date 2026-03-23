"""Tests for the extract_requirements tool."""

import json

import pytest

from tools.extract_requirements import (
    _extract_sampling_text,
    _heuristic_extract,
    _merge_extractions,
    _parse_json_response,
)


class TestParseJsonResponse:
    """Test JSON extraction from LLM responses."""

    def test_clean_json(self):
        text = '{"technical_skills": ["Python", "AWS"]}'
        result = _parse_json_response(text)
        assert result is not None
        assert result["technical_skills"] == ["Python", "AWS"]

    def test_json_in_code_block(self):
        text = '```json\n{"skills": ["Go"]}\n```'
        result = _parse_json_response(text)
        assert result is not None
        assert result["skills"] == ["Go"]

    def test_json_in_plain_code_block(self):
        text = '```\n{"key": "value"}\n```'
        result = _parse_json_response(text)
        assert result is not None
        assert result["key"] == "value"

    def test_json_with_surrounding_text(self):
        text = 'Here are the results:\n{"data": [1, 2, 3]}\nDone!'
        result = _parse_json_response(text)
        assert result is not None
        assert result["data"] == [1, 2, 3]

    def test_invalid_json(self):
        result = _parse_json_response("This is not JSON at all")
        assert result is None

    def test_empty_string(self):
        result = _parse_json_response("")
        assert result is None


class TestHeuristicExtract:
    """Test keyword-based fallback extraction."""

    def test_finds_technical_skills(self):
        text = "Must have experience with Python, Docker, and AWS."
        result = _heuristic_extract(text)
        tech = [s.lower() for s in result["technical_skills"]]
        assert "python" in tech
        assert "docker" in tech
        assert "aws" in tech

    def test_finds_soft_skills(self):
        text = "Strong communication and teamwork skills required."
        result = _heuristic_extract(text)
        soft = [s.lower() for s in result["soft_skills"]]
        assert "communication" in soft
        assert "teamwork" in soft

    def test_finds_certifications(self):
        text = "AWS Certified Solutions Architect preferred. PMP a plus."
        result = _heuristic_extract(text)
        certs = [c.lower() for c in result["certifications"]]
        assert any("aws certified" in c for c in certs)
        assert any("pmp" in c for c in certs)

    def test_finds_experience(self):
        text = "Requires 5+ years of software development experience."
        result = _heuristic_extract(text)
        assert len(result["experience"]) > 0
        assert any("5+" in e or "5" in e for e in result["experience"])

    def test_finds_education(self):
        text = "Bachelor's degree in Computer Science or related field."
        result = _heuristic_extract(text)
        assert len(result["education"]) > 0

    def test_returns_all_categories(self):
        text = "Simple job posting."
        result = _heuristic_extract(text)
        assert "technical_skills" in result
        assert "soft_skills" in result
        assert "education" in result
        assert "certifications" in result
        assert "experience" in result

    def test_empty_text(self):
        result = _heuristic_extract("")
        assert result["technical_skills"] == []
        assert result["soft_skills"] == []


class TestMergeExtractions:
    """Test merging and ranking of per-chunk extractions."""

    def test_counts_frequency(self):
        extractions = [
            {"technical_skills": ["Python", "AWS"], "soft_skills": [],
             "education": [], "certifications": [], "experience": []},
            {"technical_skills": ["Python", "Docker"], "soft_skills": [],
             "education": [], "certifications": [], "experience": []},
            {"technical_skills": ["Python"], "soft_skills": [],
             "education": [], "certifications": [], "experience": []},
        ]
        result = _merge_extractions(extractions, 3)
        tech = result["technical_skills"]
        # Python appears 3 times, should be first
        assert tech[0]["name"] == "Python"
        assert tech[0]["frequency"] == 3

    def test_sorts_by_frequency(self):
        extractions = [
            {"technical_skills": ["AWS"], "soft_skills": [],
             "education": [], "certifications": [], "experience": []},
            {"technical_skills": ["Python", "AWS"], "soft_skills": [],
             "education": [], "certifications": [], "experience": []},
        ]
        result = _merge_extractions(extractions, 2)
        tech = result["technical_skills"]
        assert tech[0]["frequency"] >= tech[-1]["frequency"]

    def test_includes_total_chunks(self):
        result = _merge_extractions([], 5)
        assert result["total_chunks_analyzed"] == 5

    def test_empty_extractions(self):
        result = _merge_extractions([], 0)
        assert result["technical_skills"] == []
        assert result["total_chunks_analyzed"] == 0

    def test_merges_all_categories(self):
        extractions = [
            {
                "technical_skills": ["Python"],
                "soft_skills": ["Communication"],
                "education": ["Bachelor's in CS"],
                "certifications": ["AWS Certified"],
                "experience": ["3+ years"],
            },
        ]
        result = _merge_extractions(extractions, 1)
        assert len(result["technical_skills"]) == 1
        assert len(result["soft_skills"]) == 1
        assert len(result["education"]) == 1
        assert len(result["certifications"]) == 1
        assert len(result["experience"]) == 1

    def test_deduplicates_case_insensitive(self):
        extractions = [
            {"technical_skills": ["python"], "soft_skills": [],
             "education": [], "certifications": [], "experience": []},
            {"technical_skills": ["Python"], "soft_skills": [],
             "education": [], "certifications": [], "experience": []},
        ]
        result = _merge_extractions(extractions, 2)
        # Should merge into one entry with frequency 2
        assert len(result["technical_skills"]) == 1
        assert result["technical_skills"][0]["frequency"] == 2


class _DummyText:
    def __init__(self, text: str):
        self.text = text


class _DummyResult:
    def __init__(self, content):
        self.content = content


class TestExtractSamplingText:
    def test_extracts_text_from_content_object(self):
        result = _DummyResult(_DummyText('{"key": "value"}'))
        assert _extract_sampling_text(result) == '{"key": "value"}'

    def test_extracts_text_from_string_content(self):
        result = _DummyResult('{"key": "value"}')
        assert _extract_sampling_text(result) == '{"key": "value"}'
