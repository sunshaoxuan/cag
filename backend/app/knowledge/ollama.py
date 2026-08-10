import json
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import httpx


class OllamaError(RuntimeError):
    pass


StructuredGenerationActivity = Callable[[dict[str, Any]], Awaitable[None]]


class OllamaProvider(Protocol):
    async def status(self) -> dict[str, Any]: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def structured_generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        timeout_seconds: int | None = None,
        activity: StructuredGenerationActivity | None = None,
    ) -> dict[str, Any]: ...


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str,
        embedding_model: str,
        memory_model: str,
        dimensions: int,
        timeout_seconds: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._embedding_model = embedding_model
        self._memory_model = memory_model
        self._dimensions = dimensions
        self._timeout = timeout_seconds

    async def status(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            version_response = await client.get(f"{self._base_url}/api/version")
            tags_response = await client.get(f"{self._base_url}/api/tags")
        if not version_response.is_success or not tags_response.is_success:
            raise OllamaError("Ollama health request failed")
        models = [
            item.get("name")
            for item in tags_response.json().get("models", [])
            if item.get("name")
        ]
        return {
            "available": True,
            "version": version_response.json().get("version"),
            "models": models,
            "embedding_model": self._embedding_model,
            "memory_model": self._memory_model,
            "dimensions": self._dimensions,
            "ready": (
                self._embedding_model in models and self._memory_model in models
            ),
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/embed",
                json={
                    "model": self._embedding_model,
                    "input": texts,
                    "dimensions": self._dimensions,
                    "truncate": True,
                    "keep_alive": "5m",
                },
            )
        if not response.is_success:
            raise OllamaError(f"Ollama embedding failed: HTTP {response.status_code}")
        embeddings = response.json().get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise OllamaError("Ollama returned an invalid embedding response")
        if any(len(item) != self._dimensions for item in embeddings):
            raise OllamaError("Ollama returned an unexpected embedding dimension")
        return embeddings

    async def structured_generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        timeout_seconds: int | None = None,
        activity: StructuredGenerationActivity | None = None,
    ) -> dict[str, Any]:
        request_timeout = timeout_seconds or self._timeout
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json={
                    "model": self._memory_model,
                    "prompt": prompt,
                    "stream": True,
                    "think": False,
                    "format": schema,
                    "options": {
                        "temperature": 0,
                        "num_ctx": 8_192,
                    },
                    "keep_alive": "5m",
                },
            ) as response:
                if not response.is_success:
                    raise OllamaError(
                        f"Ollama generation failed: HTTP {response.status_code}"
                    )
                fragments: list[str] = []
                response_chars = 0
                chunk_index = 0
                done = False
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise OllamaError(
                            "Ollama returned malformed stream data"
                        ) from exc
                    if payload.get("error"):
                        raise OllamaError("Ollama generation stream failed")
                    fragment = payload.get("response", "")
                    if not isinstance(fragment, str):
                        raise OllamaError(
                            "Ollama returned an invalid structured response"
                        )
                    fragments.append(fragment)
                    response_chars += len(fragment)
                    chunk_index += 1
                    done = payload.get("done") is True
                    if activity is not None:
                        await activity(
                            {
                                "chunk_index": chunk_index,
                                "response_chars": response_chars,
                                "done": done,
                            }
                        )
                if not done:
                    raise OllamaError(
                        "Ollama generation stream ended before completion"
                    )
        raw = "".join(fragments)
        if not raw:
            raise OllamaError("Ollama returned an invalid structured response")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned malformed JSON") from exc
        if not isinstance(parsed, dict):
            raise OllamaError("Ollama structured response must be an object")
        return parsed


class FakeOllamaClient:
    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions
        self.generated: list[str] = []
        self.embedded_texts: list[str] = []

    async def status(self) -> dict[str, Any]:
        return {
            "available": True,
            "ready": True,
            "version": "fake",
            "models": ["fake-embedding", "fake-memory"],
            "embedding_model": "fake-embedding",
            "memory_model": "fake-memory",
            "dimensions": self.dimensions,
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embedded_texts.extend(texts)
        result: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for index, byte in enumerate(text.encode("utf-8")):
                vector[index % self.dimensions] += (byte + 1) / 256.0
            norm = sum(value * value for value in vector) ** 0.5 or 1.0
            result.append([value / norm for value in vector])
        return result

    async def structured_generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        timeout_seconds: int | None = None,
        activity: StructuredGenerationActivity | None = None,
    ) -> dict[str, Any]:
        del timeout_seconds
        self.generated.append(prompt)
        if activity is not None:
            await activity(
                {"chunk_index": 1, "response_chars": 0, "done": True}
            )
        if "memories" in schema.get("properties", {}):
            return {
                "memories": [
                    {
                        "kind": "procedural",
                        "title": "Reusable investigation workflow",
                        "content": "Trace source, transformation, and verified output.",
                        "confidence": 0.9,
                    }
                ]
            }
        return {"scores": []}
