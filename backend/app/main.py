"""JobReqPilot — FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import search as search_router
from app.api.v1 import summarize as summarize_router
from app.services.cache import CacheService
from app.services.ollama_client import OllamaClient
from app.services.orchestrator import OrchestratorService
from app.services.scorer import ScorerService

log_level = os.getenv("LOG_LEVEL", "info").upper()
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

# CORS — allow the frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(search_router.router, prefix="/api/v1")
app.include_router(summarize_router.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
