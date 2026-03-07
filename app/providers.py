"""AI provider integrations — local Ollama only."""

import os
from abc import ABC, abstractmethod

import httpx


class AIProvider(ABC):
    """Base class for AI providers."""

    name: str
    models: list[str]

    @abstractmethod
    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        """Send a message and return the response."""

    def is_configured(self) -> bool:
        return True


class OllamaProvider(AIProvider):
    """Local Ollama — no API keys, fully offline."""

    name = "Ollama"
    models = ["llama3.1:8b", "mistral:7b", "gemma2:9b", "qwen2.5:7b", "phi3:mini"]

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        messages = [{"role": h["role"], "content": h["content"]} for h in history]
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]


PROVIDERS: dict[str, AIProvider] = {
    "ollama": OllamaProvider(),
}
