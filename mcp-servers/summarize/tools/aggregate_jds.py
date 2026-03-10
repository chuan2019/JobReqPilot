"""aggregate_jds tool — chunks and deduplicates job description texts.

Takes a list of raw JD texts, splits long texts into manageable chunks,
removes near-duplicate content, and returns a condensed corpus ready for
requirement extraction.
"""

import hashlib
import json
import re

from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum characters per chunk (keeps LLM context manageable)
CHUNK_SIZE = 3000
# Overlap between consecutive chunks to avoid splitting mid-sentence
CHUNK_OVERLAP = 200
# Similarity threshold for deduplication (Jaccard on word trigrams)
DEDUP_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Collapse whitespace and strip boilerplate noise."""
    # Remove common boilerplate phrases
    boilerplate = [
        r"equal\s+opportunity\s+employer",
        r"we\s+are\s+an?\s+e\.?o\.?e\.?",
        r"all\s+qualified\s+applicants",
        r"without\s+regard\s+to\s+race",
        r"click\s+here\s+to\s+apply",
        r"apply\s+now",
        r"submit\s+your\s+resume",
    ]
    cleaned = text
    for pattern in boilerplate:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks, breaking at sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence boundary (. ! ? followed by space)
        if end < len(text):
            boundary = text.rfind(". ", start + chunk_size // 2, end)
            if boundary == -1:
                boundary = text.rfind("! ", start + chunk_size // 2, end)
            if boundary == -1:
                boundary = text.rfind("? ", start + chunk_size // 2, end)
            if boundary != -1:
                end = boundary + 1  # include the punctuation

        chunks.append(text[start:end].strip())
        start = end - overlap if end < len(text) else len(text)

    return [c for c in chunks if c]


def _word_trigrams(text: str) -> set[str]:
    """Extract word-level trigrams for fuzzy comparison."""
    words = text.lower().split()
    if len(words) < 3:
        return set(words)
    return {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _deduplicate_chunks(chunks: list[str],
                        threshold: float = DEDUP_THRESHOLD) -> list[str]:
    """Remove near-duplicate chunks based on trigram Jaccard similarity."""
    if not chunks:
        return []

    unique: list[str] = []
    trigram_cache: list[set[str]] = []

    for chunk in chunks:
        chunk_trigrams = _word_trigrams(chunk)
        is_dup = False
        for existing_trigrams in trigram_cache:
            if _jaccard_similarity(chunk_trigrams, existing_trigrams) >= threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(chunk)
            trigram_cache.append(chunk_trigrams)

    return unique


def _content_hash(text: str) -> str:
    """Short hash for chunk identification."""
    return hashlib.md5(text.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_tools(server: FastMCP) -> None:
    @server.tool()
    async def aggregate_jds(jd_texts: list[str]) -> str:
        """Aggregate and deduplicate job description texts into a condensed corpus.

        Takes raw JD texts, normalizes them, splits long ones into chunks,
        removes near-duplicate content, and returns a JSON array of unique
        chunks ready for requirement extraction.

        Args:
            jd_texts: List of raw job description text strings.

        Returns:
            JSON string with metadata and deduplicated chunks:
            {
                "total_input_jds": int,
                "total_chunks": int,
                "unique_chunks": int,
                "chunks": [{"id": str, "text": str, "source_index": int}, ...]
            }
        """
        all_chunks: list[dict] = []

        for idx, raw_text in enumerate(jd_texts):
            if not raw_text or not raw_text.strip():
                continue

            normalized = _normalize_text(raw_text)
            chunks = _chunk_text(normalized)

            for chunk in chunks:
                all_chunks.append({
                    "text": chunk,
                    "source_index": idx,
                })

        total_chunks = len(all_chunks)

        # Deduplicate across all chunks
        texts_only = [c["text"] for c in all_chunks]
        unique_texts = _deduplicate_chunks(texts_only)

        # Rebuild chunk list with only unique entries
        unique_set = set(unique_texts)
        unique_chunks = []
        seen = set()
        for c in all_chunks:
            if c["text"] in unique_set and c["text"] not in seen:
                seen.add(c["text"])
                unique_chunks.append({
                    "id": _content_hash(c["text"]),
                    "text": c["text"],
                    "source_index": c["source_index"],
                })

        result = {
            "total_input_jds": len(jd_texts),
            "total_chunks": total_chunks,
            "unique_chunks": len(unique_chunks),
            "chunks": unique_chunks,
        }

        return json.dumps(result)
