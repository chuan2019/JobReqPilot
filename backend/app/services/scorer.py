"""Semantic scoring engine using embedding-based cosine similarity.

Embeds the user query and each job description via Ollama, computes cosine
similarity, and applies lightweight heuristic boosts for title match,
keyword hits, and recency.
"""

import logging
import re

import numpy as np

from app.models.search import JobResult

logger = logging.getLogger(__name__)

# Boost weights (see ARCHITECTURE.md §6)
TITLE_BOOST = 0.05
KEYWORD_BOOST_MAX = 0.03
RECENCY_BOOST = 0.02


class ScorerService:
    """Scores job results against a user query using embeddings + boosts."""

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    async def score(
        self,
        query_text: str,
        jobs: list[JobResult],
        title: str = "",
        keywords: list[str] | None = None,
        date_filter: str = "",
    ) -> list[JobResult]:
        """Score and sort jobs by semantic similarity + heuristic boosts.

        Args:
            query_text: The combined query string (title + category + keywords)
            jobs: List of JobResult objects with jd_text populated
            title: Original job title from the search request
            keywords: Original keywords from the search request
            date_filter: Original date filter from the search request

        Returns:
            Jobs sorted by match_score descending.
        """
        if not jobs:
            return []

        keywords = keywords or []

        # Build texts to embed: [query, jd_0, jd_1, ..., jd_n]
        texts_to_embed = [query_text]
        for job in jobs:
            text = job.jd_text or job.snippet
            texts_to_embed.append(text[:5000])  # Truncate for embedding

        # Embed all texts
        embeddings = await self.ollama.embed_batch(texts_to_embed)

        if not embeddings or len(embeddings) < 2:
            logger.warning("Embedding failed — returning jobs without scores")
            return jobs

        query_vec = np.array(embeddings[0])

        for i, job in enumerate(jobs):
            jd_vec = np.array(embeddings[i + 1])
            base_score = _cosine_similarity(query_vec, jd_vec)

            # Heuristic boosts
            title_boost = TITLE_BOOST if _title_match(job.title, title) else 0.0
            kw_boost = _keyword_boost(job.jd_text or job.snippet, keywords)
            date_boost = RECENCY_BOOST if date_filter and job.date_posted else 0.0

            job.match_score = float(np.clip(base_score + title_boost + kw_boost + date_boost, 0.0, 1.0))

        # Sort descending by score
        jobs.sort(key=lambda j: j.match_score, reverse=True)
        return jobs


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity, normalized to [0, 1]."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    sim = float(np.dot(a, b) / (norm_a * norm_b))
    # Normalize from [-1, 1] to [0, 1]
    return (sim + 1.0) / 2.0


def _title_match(job_title: str, query_title: str) -> bool:
    """Check if the query title appears in the job title (case-insensitive)."""
    if not query_title:
        return False
    return query_title.lower() in job_title.lower()


def _keyword_boost(text: str, keywords: list[str]) -> float:
    """Calculate keyword boost based on how many keywords appear in the text."""
    if not keywords:
        return 0.0
    text_lower = text.lower()
    matched = sum(1 for kw in keywords if kw.lower() in text_lower)
    ratio = min(matched / len(keywords), 1.0)
    return KEYWORD_BOOST_MAX * ratio
