FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies directly (this is an app, not a library)
RUN uv pip install --system --no-cache-dir \
    "mcp[cli]>=1.0.0" \
    "httpx>=0.27.0" \
    "beautifulsoup4>=4.12.0" \
    "lxml>=5.0.0"

# Copy application code
COPY server.py .
COPY tools/ tools/

EXPOSE 8001

CMD ["python", "server.py"]
