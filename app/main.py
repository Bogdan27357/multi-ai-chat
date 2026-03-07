"""Multi-AI Chat — FastAPI application."""

import asyncio
import io
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from pydantic import BaseModel

load_dotenv()

from app.ocr import DOCUMENT_TYPES, extract_text_from_image, parse_document_with_llm  # noqa: E402
from app.providers import PROVIDERS  # noqa: E402

app = FastAPI(title="Multi-AI Chat")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ---- Chat models ----

class ChatRequest(BaseModel):
    message: str
    providers: list[str]
    history: list[dict] = []


class ProviderResponse(BaseModel):
    provider: str
    model: str
    response: str
    error: str | None = None


class ChatResponse(BaseModel):
    results: list[ProviderResponse]


# ---- Pages ----

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


@app.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    doc_types = {k: v["name"] for k, v in DOCUMENT_TYPES.items()}
    return templates.TemplateResponse("documents.html", {
        "request": request,
        "document_types": doc_types,
    })


# ---- Chat API ----

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


# ---- Document OCR API ----

@app.post("/process-document")
async def process_document(
    file: UploadFile = File(...),
    doc_type: str = Form("auto"),
):
    """Upload a document image, OCR it, extract fields with LLM."""
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # Step 1: OCR
    ocr_text = extract_text_from_image(image)

    if not ocr_text:
        return {"error": "Не удалось распознать текст. Попробуйте другое изображение."}

    # Step 2: LLM extraction
    fields = await parse_document_with_llm(ocr_text, doc_type)

    # Get field labels for display
    field_labels = {}
    if doc_type != "auto" and doc_type in DOCUMENT_TYPES:
        field_labels = {code: label for code, label in DOCUMENT_TYPES[doc_type]["fields"]}

    return {
        "ocr_text": ocr_text,
        "fields": fields,
        "field_labels": field_labels,
        "doc_type": doc_type,
    }


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
