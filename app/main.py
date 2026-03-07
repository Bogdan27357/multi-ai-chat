"""Multi-AI Chat — FastAPI application."""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

load_dotenv()

from app.providers import PROVIDERS  # noqa: E402

app = FastAPI(title="Multi-AI Chat")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class ChatRequest(BaseModel):
    message: str
    providers: list[str]  # e.g. ["openai:gpt-4o", "anthropic:claude-sonnet-4-20250514"]
    history: list[dict] = []


class ProviderResponse(BaseModel):
    provider: str
    model: str
    response: str
    error: str | None = None


class ChatResponse(BaseModel):
    results: list[ProviderResponse]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    providers_info = {}
    for key, prov in PROVIDERS.items():
        providers_info[key] = {
            "name": prov.name,
            "models": prov.models,
            "configured": prov.is_configured(),
        }
    return templates.TemplateResponse("index.html", {
        "request": request,
        "providers": providers_info,
    })


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    tasks = []
    task_meta = []

    for entry in req.providers:
        provider_key, model = entry.split(":", 1)
        provider = PROVIDERS.get(provider_key)
        if not provider:
            continue
        tasks.append(provider.chat(req.message, model, req.history))
        task_meta.append((provider_key, model))

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for (provider_key, model), resp in zip(task_meta, responses):
        if isinstance(resp, Exception):
            results.append(ProviderResponse(
                provider=provider_key,
                model=model,
                response="",
                error=str(resp),
            ))
        else:
            results.append(ProviderResponse(
                provider=provider_key,
                model=model,
                response=resp,
            ))

    return ChatResponse(results=results)


@app.get("/providers")
async def list_providers():
    result = {}
    for key, prov in PROVIDERS.items():
        result[key] = {
            "name": prov.name,
            "models": prov.models,
            "configured": prov.is_configured(),
        }
    return result
