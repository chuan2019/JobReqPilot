"""JobReqPilot — Summarize MCP Server.

Exposes tools over SSE transport:
  - aggregate_jds:          Chunk & deduplicate JD content
  - extract_requirements:   Extract structured requirements from JD corpus
"""

import os

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    name="summarize",
    instructions="Summarization MCP server for JobReqPilot. Provides tools to "
    "aggregate job descriptions and extract structured requirements.",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8002")),
)

# Import tools — decorators register them on the server instance
from tools.aggregate_jds import register_tools as register_aggregate_jds
from tools.extract_requirements import register_tools as register_extract_requirements

register_aggregate_jds(server)
register_extract_requirements(server)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "sse")
    server.run(transport=transport)
