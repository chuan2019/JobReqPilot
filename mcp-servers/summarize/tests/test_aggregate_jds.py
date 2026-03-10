"""Tests for the aggregate_jds tool."""

import json

import pytest

from tools.aggregate_jds import (
    _chunk_text,
    _deduplicate_chunks,
    _jaccard_similarity,
    _normalize_text,
    _word_trigrams,
)


class TestNormalizeText:
    """Test boilerplate removal and whitespace normalization."""

    def test_collapses_whitespace(self):
        result = _normalize_text("Hello   world\n\nfoo   bar")
        assert result == "Hello world foo bar"

    def test_removes_eoe_boilerplate(self):
        text = "We need Python skills. We are an Equal Opportunity Employer."
        result = _normalize_text(text)
        assert "equal opportunity employer" not in result.lower()

    def test_removes_apply_now(self):
        text = "Great job posting. Apply Now to join our team."
        result = _normalize_text(text)
        assert "apply now" not in result.lower()

    def test_preserves_meaningful_content(self):
        text = "Requires 5 years of Python experience with AWS and Docker."
        result = _normalize_text(text)
        assert "Python" in result
        assert "AWS" in result
        assert "Docker" in result


class TestChunkText:
    """Test text chunking logic."""

    def test_short_text_single_chunk(self):
        text = "This is a short text."
        chunks = _chunk_text(text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        # Create text longer than chunk size
        text = "Word " * 1000  # ~5000 chars
        chunks = _chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) > 1
        # All chunks should be non-empty
        assert all(c.strip() for c in chunks)

    def test_empty_text(self):
        chunks = _chunk_text("")
        assert chunks == [""]

    def test_respects_chunk_size(self):
        text = "A" * 10000
        chunks = _chunk_text(text, chunk_size=3000, overlap=200)
        # Each chunk should be at most chunk_size
        for chunk in chunks:
            assert len(chunk) <= 3000


class TestWordTrigrams:
    """Test trigram extraction."""

    def test_basic_trigrams(self):
        trigrams = _word_trigrams("the quick brown fox")
        assert "the quick brown" in trigrams
        assert "quick brown fox" in trigrams
        assert len(trigrams) == 2

    def test_short_text(self):
        trigrams = _word_trigrams("hello world")
        # Fewer than 3 words returns the words as a set
        assert "hello" in trigrams or "world" in trigrams

    def test_case_insensitive(self):
        trigrams = _word_trigrams("The Quick Brown")
        assert "the quick brown" in trigrams


class TestJaccardSimilarity:
    """Test Jaccard similarity computation."""

    def test_identical_sets(self):
        s = {"a", "b", "c"}
        assert _jaccard_similarity(s, s) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        sim = _jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert sim == pytest.approx(0.5)  # 2/4

    def test_empty_sets(self):
        assert _jaccard_similarity(set(), set()) == 0.0
        assert _jaccard_similarity({"a"}, set()) == 0.0


class TestDeduplicateChunks:
    """Test near-duplicate removal."""

    def test_removes_exact_duplicates(self):
        chunks = ["Hello world foo bar", "Hello world foo bar"]
        result = _deduplicate_chunks(chunks, threshold=0.5)
        assert len(result) == 1

    def test_keeps_distinct_chunks(self):
        chunks = [
            "Python developer needed with AWS experience and Docker",
            "Marketing manager for social media campaigns and branding",
        ]
        result = _deduplicate_chunks(chunks, threshold=0.7)
        assert len(result) == 2

    def test_empty_list(self):
        assert _deduplicate_chunks([]) == []

    def test_single_chunk(self):
        result = _deduplicate_chunks(["Only chunk"])
        assert result == ["Only chunk"]


class TestAggregateJdsIntegration:
    """Integration tests for the full aggregation pipeline."""

    @pytest.mark.asyncio
    async def test_aggregate_basic(self):
        """Test aggregate_jds produces valid output structure."""
        # We test the helper functions directly since the tool
        # requires an MCP server context
        jd1 = "We need a Python developer with 3 years of experience."
        jd2 = "Looking for a Java engineer with cloud experience."

        # Simulate what aggregate_jds does
        normalized1 = _normalize_text(jd1)
        normalized2 = _normalize_text(jd2)
        chunks1 = _chunk_text(normalized1)
        chunks2 = _chunk_text(normalized2)

        all_texts = chunks1 + chunks2
        unique = _deduplicate_chunks(all_texts)

        assert len(unique) == 2
        assert any("Python" in c for c in unique)
        assert any("Java" in c for c in unique)
