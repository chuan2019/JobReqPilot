"""JobReqPilot — FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import search as search_router
from app.api.v1 import summarize as summarize_router
from app.errors import register_error_handlers
from app.middleware import RateLimitMiddleware, RequestTimingMiddleware
from app.services.cache import CacheService
from app.services.ollama_client import OllamaClient
from app.services.orchestrator import OrchestratorService
from app.services.scorer import ScorerService

log_level = os.getenv("LOG_LEVEL", "info").upper()
log_format = os.getenv("LOG_FORMAT", "text")  # "text" or "json"

if log_format == "json":
    import json as _json

    class _JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            return _json.dumps({
                "time": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            })

    _handler = logging.StreamHandler()
    _handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), handlers=[_handler])
else:
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for shared services."""
    # Startup
    ollama = OllamaClient()
    await ollama.start()

    cache = CacheService()
    await cache.start()

    # Share Redis connection for embedding caching
    if cache._redis:
        ollama.set_cache(cache._redis)

    scorer = ScorerService(ollama)
    orchestrator = OrchestratorService(ollama)

    # Store services on app state for access from endpoints
    app.state.ollama = ollama
    app.state.cache = cache
    app.state.scorer = scorer
    app.state.orchestrator = orchestrator

    logger.info("JobReqPilot backend started")
    yield

    # Shutdown
    await cache.stop()
    await ollama.stop()
    logger.info("JobReqPilot backend stopped")


app = FastAPI(
    title="JobReqPilot",
    description="MCP-powered job search and requirements analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters: last added = first executed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestTimingMiddleware)

# Register error handlers and API routes
register_error_handlers(app)
app.include_router(search_router.router, prefix="/api/v1")
app.include_router(summarize_router.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
