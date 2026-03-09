"""build_query tool — generates an optimized boolean search query.

Uses MCP sampling to delegate LLM calls to the host (orchestrator),
keeping this server fully model-agnostic.
"""

import json

from mcp.server.fastmcp import Context, FastMCP


def register_tools(server: FastMCP) -> None:
    @server.tool()
    async def build_query(
        title: str,
        category: str = "",
        keywords: list[str] | None = None,
        ctx: Context = None,
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

        # Use MCP sampling — delegates the LLM call to the host/orchestrator.
        # If sampling is not available, fall back to a simple heuristic query.
        try:
            result = await ctx.session.create_message(
                messages=[
                    {
                        "role": "user",
                        "content": {"type": "text", "text": prompt},
                    }
                ],
                max_tokens=512,
            )
            # Extract text from the sampling result
            if hasattr(result, "content"):
                if isinstance(result.content, str):
                    return result.content
                if hasattr(result.content, "text"):
                    return result.content.text
            return str(result)
        except Exception as e:
            if ctx:
                ctx.info(f"Sampling unavailable ({e}), using heuristic query builder")
            return _heuristic_query(title, category, kw_list)


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
