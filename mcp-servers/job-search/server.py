"""JobReqPilot — Job Search MCP Server.

Exposes three tools over SSE transport:
  - build_query:  Generate an optimized search query from user inputs
  - search_jobs:  Search job boards via Tavily Search API
  - scrape_jd:    Scrape and parse job description pages
"""

import os

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    name="job-search",
    instructions="Job search MCP server for JobReqPilot. Provides tools to build "
    "search queries, search job boards, and scrape job descriptions.",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8001")),
)

# Import tools — decorators register them on the server instance
from tools.build_query import register_tools as register_build_query
from tools.search_jobs import register_tools as register_search_jobs
from tools.scrape_jd import register_tools as register_scrape_jd

register_build_query(server)
register_search_jobs(server)
register_scrape_jd(server)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "sse")
    server.run(transport=transport)
