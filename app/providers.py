"""AI provider integrations for Multi-AI Chat (free tier only)."""

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
        """Check if the provider API key is set."""
        return True


class GroqProvider(AIProvider):
    """Groq — free tier, OpenAI-compatible API. Models: Llama 3, Mixtral, Gemma."""

    name = "Groq"
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        if not self.is_configured():
            return "[Groq API key not configured]"

        messages = [{"role": h["role"], "content": h["content"]} for h in history]
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


class GoogleProvider(AIProvider):
    """Google Gemini — free tier (15 RPM, 1M tokens/day)."""

    name = "Google"
    models = ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
        self._configured = bool(api_key)

    def is_configured(self) -> bool:
        return self._configured

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        if not self.is_configured():
            return "[Google API key not configured]"

        gen_model = genai.GenerativeModel(model)

        gemini_history = []
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [h["content"]]})

        chat = gen_model.start_chat(history=gemini_history)
        response = await chat.send_message_async(message)
        return response.text


class CohereProvider(AIProvider):
    """Cohere — free tier (rate-limited). Models: Command R."""

    name = "Cohere"
    models = ["command-r-plus", "command-r", "command-light"]

    def __init__(self):
        self.api_key = os.getenv("COHERE_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        if not self.is_configured():
            return "[Cohere API key not configured]"

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
            data = resp.json()
            return data["text"]


# Registry of all providers
PROVIDERS: dict[str, AIProvider] = {
    "groq": GroqProvider(),
    "google": GoogleProvider(),
    "cohere": CohereProvider(),
}
