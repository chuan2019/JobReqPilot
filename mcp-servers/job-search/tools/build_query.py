"""build_query tool — generates an optimized boolean search query.

Uses MCP sampling to delegate LLM calls to the host (orchestrator),
keeping this server fully model-agnostic.
"""

import json
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP
import mcp.types as types


def register_tools(server: FastMCP) -> None:
    @server.tool()
    async def build_query(
        title: str,
        category: str = "",
        keywords: list[str] | None = None,
        ctx: Optional[Context] = None,
    ) -> str:
        """Build an optimized boolean search query for job boards.

        Args:
            title: Job title to search for (e.g. "Software Engineer")
            category: Job category or industry (e.g. "Technology", "Finance")
            keywords: Additional keywords to include (e.g. ["Python", "remote"])

        Returns:
            A structured JSON string with the optimized query and metadata.
        """
        kw_list = keywords or []
        kw_str = ", ".join(kw_list) if kw_list else "none"

        prompt = (
            f"Generate an optimized boolean search query for job boards.\n\n"
            f"Job title: {title}\n"
            f"Category: {category or 'any'}\n"
            f"Keywords: {kw_str}\n\n"
            f"Return ONLY a JSON object with these fields:\n"
            f'  "query": the boolean search string (use AND, OR, quotes for phrases)\n'
            f'  "title_variants": list of title synonyms/variations to broaden the search\n'
            f'  "excluded_terms": list of terms to exclude with NOT\n\n'
            f"Example output:\n"
            f'{{"query": "\\"Software Engineer\\" OR \\"SWE\\" AND (Python OR Java)", '
            f'"title_variants": ["Software Developer", "SWE", "Backend Engineer"], '
            f'"excluded_terms": ["intern", "internship"]}}'
        )

        # Use MCP sampling when a session is available; otherwise use heuristics.
        if ctx and getattr(ctx, "session", None):
            try:
                messages = [
                    types.SamplingMessage(
                        role="user",
                        content=types.TextContent(type="text", text=prompt),
                    )
                ]
                result = await ctx.session.create_message(
                    messages=messages,
                    max_tokens=512,
                )
                sampled = _extract_sampling_text(result)
                if sampled:
                    return sampled
            except Exception as e:
                ctx.info(f"Sampling unavailable ({e}), using heuristic query builder")

        return _heuristic_query(title, category, kw_list)


def _extract_sampling_text(result: object) -> str:
    """Extract text from MCP sampling result content."""
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    text = getattr(content, "text", None)
    if isinstance(text, str):
        return text
    return str(result or "")


def _heuristic_query(
    title: str, category: str, keywords: list[str]
) -> str:
    """Fallback query builder when MCP sampling is not available."""
    parts = [f'"{title}"']

    if category:
        parts.append(f'"{category}"')

    if keywords:
        kw_group = " OR ".join(f'"{kw}"' for kw in keywords)
        parts.append(f"({kw_group})")

    query = " AND ".join(parts)

    result = {
        "query": query,
        "title_variants": [title],
        "excluded_terms": [],
    }
    return json.dumps(result)
