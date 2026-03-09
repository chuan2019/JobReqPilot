"""Async client for the Ollama REST API.

Handles text generation (/api/generate) and embeddings (/api/embeddings).
Reads model configuration from environment variables and validates model
availability at startup.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

FALLBACK_LLM_ORDER = ["llama3.2", "llama3.1:8b", "mistral", "qwen2:7b"]
FALLBACK_EMBED_ORDER = ["nomic-embed-text", "mxbai-embed-large", "all-minilm"]


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
        payload = {"model": self.embed_model, "prompt": text}
        response = await self.client.post("/api/embeddings", json=payload)
        response.raise_for_status()
        return response.json().get("embedding", [])

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts sequentially."""
        results = []
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

        # Check exact match
        if preferred in available:
            return preferred

        # Check if the preferred model matches without tag (e.g. "llama3.2" matches "llama3.2:latest")
        for name in available:
            if name.split(":")[0] == preferred.split(":")[0]:
                logger.info("Resolved '%s' to '%s'", preferred, name)
                return name

        # Try fallbacks
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
