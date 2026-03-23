"""extract_requirements tool — extracts and ranks structured requirements from JD chunks.

Uses MCP sampling to delegate LLM calls to the host (orchestrator),
keeping this server fully model-agnostic. Processes chunks individually,
then merges and ranks requirements across all chunks.
"""

import json
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP
import mcp.types as types


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

EXTRACT_PROMPT = """\
Analyze the following job description text and extract ALL requirements mentioned.

Job Description:
{jd_text}

Return ONLY a JSON object with these fields:
  "technical_skills": list of technical skills/tools/languages required
  "soft_skills": list of soft skills mentioned
  "education": list of education requirements (degrees, fields of study)
  "certifications": list of certifications or licenses mentioned
  "experience": list of experience requirements (years, domains)

Each item should be a short, normalized phrase (e.g. "Python" not "experience with Python programming language").

Example output:
{{"technical_skills": ["Python", "AWS", "Docker", "REST APIs"], \
"soft_skills": ["communication", "teamwork", "problem-solving"], \
"education": ["Bachelor's in Computer Science"], \
"certifications": ["AWS Solutions Architect"], \
"experience": ["3+ years software development", "cloud infrastructure"]}}
"""

MERGE_PROMPT = """\
You are given extracted requirements from {num_chunks} job description chunks.
Merge and rank them by frequency. Requirements that appear in more chunks are more important.

Per-chunk extractions:
{chunk_extractions}

Return ONLY a JSON object with these fields:
  "technical_skills": list of objects {{"name": str, "frequency": int}}
  "soft_skills": list of objects {{"name": str, "frequency": int}}
  "education": list of objects {{"name": str, "frequency": int}}
  "certifications": list of objects {{"name": str, "frequency": int}}
  "experience": list of objects {{"name": str, "frequency": int}}
  "total_chunks_analyzed": int

Sort each list by frequency (descending). Deduplicate similar items \
(e.g. "Python 3" and "Python" should be merged as "Python"). \
Normalize names to title case for skills and certifications.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> dict | None:
    """Try to extract a JSON object from an LLM response."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in markdown code blocks
    import re
    patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
        r"\{.*\}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if "```" in pattern else match.group(0))
            except (json.JSONDecodeError, IndexError):
                continue
    return None


def _heuristic_extract(jd_text: str) -> dict:
    """Fallback extraction using keyword matching when LLM sampling is unavailable."""
    text_lower = jd_text.lower()

    # Common technical skills to look for
    tech_keywords = [
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
        "sql", "nosql", "mongodb", "postgresql", "mysql", "redis",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "react", "angular", "vue", "node.js", "fastapi", "django", "flask",
        "git", "ci/cd", "jenkins", "github actions",
        "rest api", "graphql", "microservices", "machine learning", "deep learning",
        "linux", "agile", "scrum", "jira",
    ]

    # Common soft skills
    soft_keywords = [
        "communication", "teamwork", "leadership", "problem-solving",
        "analytical", "detail-oriented", "self-motivated", "collaborative",
        "time management", "critical thinking", "adaptability",
    ]

    # Common certifications
    cert_keywords = [
        "aws certified", "azure certified", "pmp", "scrum master",
        "cissp", "cisa", "comptia", "google certified",
    ]

    found_tech = [kw.title() for kw in tech_keywords if kw in text_lower]
    found_soft = [kw.title() for kw in soft_keywords if kw in text_lower]
    found_certs = [kw.title() for kw in cert_keywords if kw in text_lower]

    # Extract education mentions
    education = []
    import re
    edu_patterns = [
        r"(?:bachelor'?s?|b\.?s\.?|b\.?a\.?)\s+(?:degree\s+)?(?:in\s+)?[\w\s]+",
        r"(?:master'?s?|m\.?s\.?|m\.?a\.?)\s+(?:degree\s+)?(?:in\s+)?[\w\s]+",
        r"(?:ph\.?d\.?|doctorate)\s+(?:in\s+)?[\w\s]+",
    ]
    for pattern in edu_patterns:
        matches = re.findall(pattern, text_lower)
        education.extend(m.strip().title() for m in matches[:2])

    # Extract experience mentions
    experience = []
    exp_pattern = r"(\d+\+?\s*(?:years?|yrs?)[\w\s]*?)(?:\.|,|;|\n)"
    exp_matches = re.findall(exp_pattern, text_lower)
    experience.extend(m.strip().title() for m in exp_matches[:5])

    return {
        "technical_skills": found_tech,
        "soft_skills": found_soft,
        "education": education if education else [],
        "certifications": found_certs,
        "experience": experience if experience else [],
    }


def _merge_extractions(extractions: list[dict], num_chunks: int) -> dict:
    """Merge multiple per-chunk extractions by counting frequency."""
    categories = [
        "technical_skills", "soft_skills", "education",
        "certifications", "experience",
    ]

    merged: dict[str, dict[str, int]] = {cat: {} for cat in categories}

    for extraction in extractions:
        for cat in categories:
            items = extraction.get(cat, [])
            for item in items:
                # Normalize: strip whitespace, title case
                name = item.strip()
                if not name:
                    continue
                key = name.lower()
                if key in merged[cat]:
                    merged[cat][key] = (merged[cat][key][0], merged[cat][key][1] + 1)
                else:
                    merged[cat][key] = (name, 1)

    # Build ranked result
    result: dict = {"total_chunks_analyzed": num_chunks}
    for cat in categories:
        items = [
            {"name": name, "frequency": freq}
            for name, freq in merged[cat].values()
        ]
        items.sort(key=lambda x: x["frequency"], reverse=True)
        result[cat] = items

    return result


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_tools(server: FastMCP) -> None:
    @server.tool()
    async def extract_requirements(
        chunks: list[str],
        ctx: Optional[Context] = None,
    ) -> str:
        """Extract and rank structured requirements from job description chunks.

        Takes a list of JD text chunks (from aggregate_jds) and extracts
        requirements using the LLM. First extracts per-chunk, then merges
        and ranks by frequency across all chunks.

        Args:
            chunks: List of JD text chunks to analyze.

        Returns:
            JSON string with ranked requirements:
            {
                "total_chunks_analyzed": int,
                "technical_skills": [{"name": str, "frequency": int}, ...],
                "soft_skills": [{"name": str, "frequency": int}, ...],
                "education": [{"name": str, "frequency": int}, ...],
                "certifications": [{"name": str, "frequency": int}, ...],
                "experience": [{"name": str, "frequency": int}, ...]
            }
        """
        if not chunks:
            return json.dumps({
                "total_chunks_analyzed": 0,
                "technical_skills": [],
                "soft_skills": [],
                "education": [],
                "certifications": [],
                "experience": [],
            })

        per_chunk_extractions: list[dict] = []
        use_sampling = bool(ctx and getattr(ctx, "session", None))

        # Step 1: Extract requirements from each chunk
        for chunk_text in chunks:
            if not chunk_text.strip():
                continue

            if use_sampling:
                try:
                    prompt = EXTRACT_PROMPT.format(jd_text=chunk_text)
                    result = await ctx.session.create_message(
                        messages=[
                            types.SamplingMessage(
                                role="user",
                                content=types.TextContent(type="text", text=prompt),
                            )
                        ],
                        max_tokens=1024,
                    )

                    response_text = _extract_sampling_text(result)

                    parsed = _parse_json_response(response_text)
                    if parsed:
                        per_chunk_extractions.append(parsed)
                    else:
                        # LLM returned non-JSON, fall back for this chunk
                        per_chunk_extractions.append(
                            _heuristic_extract(chunk_text)
                        )

                except Exception as e:
                    if ctx:
                        ctx.info(
                            f"Sampling failed ({e}), falling back to heuristic"
                        )
                    use_sampling = False
                    per_chunk_extractions.append(
                        _heuristic_extract(chunk_text)
                    )
            else:
                per_chunk_extractions.append(_heuristic_extract(chunk_text))

        if not per_chunk_extractions:
            return json.dumps({
                "total_chunks_analyzed": 0,
                "technical_skills": [],
                "soft_skills": [],
                "education": [],
                "certifications": [],
                "experience": [],
            })

        # Step 2: Merge and rank across all chunks
        # Try LLM-based merging first, fall back to heuristic
        if use_sampling:
            try:
                merge_prompt = MERGE_PROMPT.format(
                    num_chunks=len(per_chunk_extractions),
                    chunk_extractions=json.dumps(
                        per_chunk_extractions, indent=2
                    ),
                )
                result = await ctx.session.create_message(
                    messages=[
                        types.SamplingMessage(
                            role="user",
                            content=types.TextContent(type="text", text=merge_prompt),
                        )
                    ],
                    max_tokens=2048,
                )

                response_text = _extract_sampling_text(result)

                parsed = _parse_json_response(response_text)
                if parsed:
                    # Ensure total_chunks_analyzed is set
                    parsed["total_chunks_analyzed"] = len(
                        per_chunk_extractions
                    )
                    return json.dumps(parsed)

            except Exception as e:
                if ctx:
                    ctx.info(
                        f"Sampling merge failed ({e}), using heuristic merge"
                    )

        # Heuristic merge fallback
        merged = _merge_extractions(
            per_chunk_extractions, len(per_chunk_extractions)
        )
        return json.dumps(merged)


def _extract_sampling_text(result: object) -> str:
    """Extract text from MCP sampling result content."""
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    text = getattr(content, "text", None)
    if isinstance(text, str):
        return text
    return str(result or "")
