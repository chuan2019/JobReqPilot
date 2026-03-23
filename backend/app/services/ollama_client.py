"""Async client for the Ollama REST API.

Handles text generation (/api/generate) and embeddings (/api/embeddings).
Reads model configuration from environment variables and validates model
availability at startup. Supports Redis-backed embedding caching.
"""

import hashlib
import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

FALLBACK_LLM_ORDER = ["llama3.2", "llama3.1:8b", "mistral", "qwen2:7b"]
FALLBACK_EMBED_ORDER = ["nomic-embed-text", "mxbai-embed-large", "all-minilm"]

EMBED_CACHE_TTL = 86400  # 24 hours


class OllamaClient:
    """Thin async wrapper around Ollama's REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        llm_model: str | None = None,
        embed_model: str | None = None,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")).rstrip("/")
        self.llm_model = llm_model or os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
        self.embed_model = embed_model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self._client: httpx.AsyncClient | None = None
        self._redis = None  # Set via set_cache()

    def set_cache(self, redis_client) -> None:
        """Attach a Redis client for embedding caching."""
        self._redis = redis_client

    async def start(self) -> None:
        """Create the HTTP client and validate models."""
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        self.llm_model = await self._resolve_model(self.llm_model, FALLBACK_LLM_ORDER)
        self.embed_model = await self._resolve_model(self.embed_model, FALLBACK_EMBED_ORDER)
        logger.info("Ollama client ready — LLM: %s, Embed: %s", self.llm_model, self.embed_model)

    async def stop(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("OllamaClient not started — call start() first")
        return self._client

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
        """Generate text using the configured LLM model."""
        payload: dict = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if system:
            payload["system"] = system

        response = await self.client.post("/api/generate", json=payload)
        response.raise_for_status()
        return response.json().get("response", "")

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        cache_key = self._embed_cache_key(text)
        cached = await self._get_cached_embedding(cache_key)
        if cached is not None:
            return cached

        payload = {"model": self.embed_model, "prompt": text}
        response = await self.client.post("/api/embeddings", json=payload)
        response.raise_for_status()
        embedding = response.json().get("embedding", [])

        await self._set_cached_embedding(cache_key, embedding)
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts, using cache where possible."""
        results: list[list[float]] = []
        for text in texts:
            vec = await self.embed(text)
            results.append(vec)
        return results

    async def list_models(self) -> set[str]:
        """List all models available in Ollama."""
        response = await self.client.get("/api/tags")
        response.raise_for_status()
        return {m["name"] for m in response.json().get("models", [])}

    async def _resolve_model(self, preferred: str, fallback_order: list[str]) -> str:
        """Validate that the preferred model exists, falling back if needed."""
        try:
            available = await self.list_models()
        except httpx.HTTPError as e:
            logger.warning("Cannot reach Ollama to validate models: %s", e)
            return preferred

        if preferred in available:
            return preferred

        for name in available:
            if name.split(":")[0] == preferred.split(":")[0]:
                logger.info("Resolved '%s' to '%s'", preferred, name)
                return name

        for fallback in fallback_order:
            for name in available:
                if name.split(":")[0] == fallback.split(":")[0]:
                    logger.warning("Model '%s' not found, falling back to '%s'", preferred, name)
                    return name

        logger.error(
            "No suitable model found. Available: %s. Pull one with: "
            "docker compose run --rm ollama ollama pull %s",
            available,
            fallback_order[0],
        )
        return preferred

    # ── Embedding cache helpers ──

    def _embed_cache_key(self, text: str) -> str:
        """Generate a cache key for an embedding based on content hash."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"embed:{self.embed_model}:{content_hash}"

    async def _get_cached_embedding(self, key: str) -> list[float] | None:
        """Retrieve a cached embedding from Redis."""
        if not self._redis:
            return None
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return None

    async def _set_cached_embedding(self, key: str, embedding: list[float]) -> None:
        """Store an embedding in Redis with TTL."""
        if not self._redis or not embedding:
            return
        try:
            await self._redis.set(key, json.dumps(embedding), ex=EMBED_CACHE_TTL)
        except Exception:
            pass
