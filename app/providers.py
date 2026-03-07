"""AI provider integrations — local Ollama + free cloud services."""

import os
from abc import ABC, abstractmethod

import httpx
import google.generativeai as genai


class AIProvider(ABC):
    """Base class for AI providers."""

    name: str
    models: list[str]

    @abstractmethod
    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        """Send a message and return the response."""

    def is_configured(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Local: Ollama
# ---------------------------------------------------------------------------

class OllamaProvider(AIProvider):
    """Local Ollama — no API keys, fully offline."""

    name = "Ollama (локально)"
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


# ---------------------------------------------------------------------------
# Cloud free tier: Google Gemini
# ---------------------------------------------------------------------------

class GoogleProvider(AIProvider):
    """Google Gemini — free tier (15 RPM, 1M tokens/day)."""

    name = "Google Gemini"
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
        self._configured = bool(api_key)

    def is_configured(self) -> bool:
        return self._configured

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        gen_model = genai.GenerativeModel(model)
        gemini_history = []
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [h["content"]]})
        chat = gen_model.start_chat(history=gemini_history)
        response = await chat.send_message_async(message)
        return response.text


# ---------------------------------------------------------------------------
# Cloud free tier: Groq
# ---------------------------------------------------------------------------

class GroqProvider(AIProvider):
    """Groq — free tier (30 RPM, 14 400 req/day). Very fast."""

    name = "Groq"
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        messages = [{"role": h["role"], "content": h["content"]} for h in history]
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "messages": messages, "max_tokens": 4096},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Cloud free tier: Cohere
# ---------------------------------------------------------------------------

class CohereProvider(AIProvider):
    """Cohere — free tier (20 RPM). Command R models."""

    name = "Cohere"
    models = ["command-r-plus", "command-r"]

    def __init__(self):
        self.api_key = os.getenv("COHERE_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        chat_history = []
        for h in history:
            role = "USER" if h["role"] == "user" else "CHATBOT"
            chat_history.append({"role": role, "message": h["content"]})

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.cohere.com/v1/chat",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "message": message,
                    "chat_history": chat_history,
                },
            )
            resp.raise_for_status()
            return resp.json()["text"]


# ---------------------------------------------------------------------------
# Cloud free tier: HuggingFace Inference API
# ---------------------------------------------------------------------------

class HuggingFaceProvider(AIProvider):
    """HuggingFace Inference API — free tier. Open-source models."""

    name = "HuggingFace"
    models = [
        "mistralai/Mistral-7B-Instruct-v0.3",
        "microsoft/Phi-3-mini-4k-instruct",
    ]

    def __init__(self):
        self.api_key = os.getenv("HUGGINGFACE_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        messages = [{"role": h["role"], "content": h["content"]} for h in history]
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "messages": messages, "max_tokens": 2048},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, AIProvider] = {
    "ollama": OllamaProvider(),
    "google": GoogleProvider(),
    "groq": GroqProvider(),
    "cohere": CohereProvider(),
    "huggingface": HuggingFaceProvider(),
}
