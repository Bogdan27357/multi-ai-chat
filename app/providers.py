"""AI provider integrations for Multi-AI Chat."""

import os
from abc import ABC, abstractmethod

import anthropic
import openai
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


class OpenAIProvider(AIProvider):
    name = "OpenAI"
    models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = openai.AsyncOpenAI(api_key=api_key) if api_key else None

    def is_configured(self) -> bool:
        return self.client is not None and bool(os.getenv("OPENAI_API_KEY"))

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        if not self.is_configured():
            return "[OpenAI API key not configured]"

        messages = [{"role": h["role"], "content": h["content"]} for h in history]
        messages.append({"role": "user", "content": message})

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content


class AnthropicProvider(AIProvider):
    name = "Anthropic"
    models = ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001", "claude-3-5-sonnet-20241022"]

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else None

    def is_configured(self) -> bool:
        return self.client is not None and bool(os.getenv("ANTHROPIC_API_KEY"))

    async def chat(self, message: str, model: str, history: list[dict]) -> str:
        if not self.is_configured():
            return "[Anthropic API key not configured]"

        messages = [{"role": h["role"], "content": h["content"]} for h in history]
        messages.append({"role": "user", "content": message})

        response = await self.client.messages.create(
            model=model,
            max_tokens=4096,
            messages=messages,
        )
        return response.content[0].text


class GoogleProvider(AIProvider):
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


# Registry of all providers
PROVIDERS: dict[str, AIProvider] = {
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "google": GoogleProvider(),
}
