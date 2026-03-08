"""Multi-AI Chat — FastAPI application."""

import asyncio
import io
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from pydantic import BaseModel

load_dotenv()

from app.database import (  # noqa: E402
    add_document,
    create_employee,
    delete_document,
    delete_employee,
    get_employee,
    get_employee_documents,
    get_employee_merged_fields,
    init_db,
    list_employees,
    update_employee,
)
from app.ocr import DOCUMENT_TYPES, extract_text_from_image, parse_document_with_llm  # noqa: E402
from app.providers import PROVIDERS  # noqa: E402
from app.questionnaire import generate_questionnaire  # noqa: E402

app = FastAPI(title="Multi-AI Chat")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
async def startup():
    init_db()


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


@app.get("/employees", response_class=HTMLResponse)
async def employees_page(request: Request):
    return templates.TemplateResponse("employees.html", {"request": request})


@app.get("/employees/{employee_id}", response_class=HTMLResponse)
async def employee_profile_page(request: Request, employee_id: int):
    emp = get_employee(employee_id)
    if emp is None:
        return HTMLResponse("<h1>Сотрудник не найден</h1>", status_code=404)
    doc_types = {k: v["name"] for k, v in DOCUMENT_TYPES.items()}
    return templates.TemplateResponse("employee_profile.html", {
        "request": request,
        "employee": emp,
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


@app.post("/generate-questionnaire")
async def gen_questionnaire(request: Request):
    """Generate a DOCX questionnaire from extracted fields."""
    data = await request.json()
    fields = data.get("fields", {})

    buf = generate_questionnaire(fields)

    surname = fields.get("surname", "работник")
    filename = f"anketa_{surname}.docx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/providers")
async def list_providers_api():
    result = {}
    for key, prov in PROVIDERS.items():
        result[key] = {
            "name": prov.name,
            "models": prov.models,
            "configured": prov.is_configured(),
        }
    return result


# ---- Employees API ----

@app.get("/api/employees")
async def api_list_employees(search: str = ""):
    employees = list_employees(search)
    return {"employees": employees}


@app.post("/api/employees")
async def api_create_employee(request: Request):
    data = await request.json()
    emp_id = create_employee(data)
    return {"id": emp_id}


@app.get("/api/employees/{employee_id}")
async def api_get_employee(employee_id: int):
    emp = get_employee(employee_id)
    if emp is None:
        return JSONResponse({"error": "Сотрудник не найден"}, status_code=404)
    return emp


@app.put("/api/employees/{employee_id}")
async def api_update_employee(employee_id: int, request: Request):
    data = await request.json()
    ok = update_employee(employee_id, data)
    if not ok:
        return JSONResponse({"error": "Не удалось обновить"}, status_code=400)
    return {"ok": True}


@app.delete("/api/employees/{employee_id}")
async def api_delete_employee(employee_id: int):
    ok = delete_employee(employee_id)
    if not ok:
        return JSONResponse({"error": "Сотрудник не найден"}, status_code=404)
    return {"ok": True}


# ---- Employee Documents API ----

@app.get("/api/employees/{employee_id}/documents")
async def api_get_documents(employee_id: int):
    docs = get_employee_documents(employee_id)
    return {"documents": docs}


@app.post("/api/employees/{employee_id}/documents")
async def api_add_document(employee_id: int, request: Request):
    data = await request.json()
    doc_id = add_document(
        employee_id,
        data.get("doc_type", "auto"),
        data.get("fields", {}),
        data.get("ocr_text", ""),
    )
    # Auto-update employee base fields from document
    fields = data.get("fields", {})
    update_data = {}
    for key in ("surname", "name", "patronymic", "birth_date", "birth_place", "gender"):
        if fields.get(key):
            update_data[key] = fields[key]
    if update_data:
        update_employee(employee_id, update_data)
    return {"id": doc_id}


@app.delete("/api/documents/{doc_id}")
async def api_delete_document(doc_id: int):
    ok = delete_document(doc_id)
    if not ok:
        return JSONResponse({"error": "Документ не найден"}, status_code=404)
    return {"ok": True}


@app.post("/api/employees/{employee_id}/questionnaire")
async def api_employee_questionnaire(employee_id: int):
    """Generate a DOCX questionnaire from all employee documents."""
    fields = get_employee_merged_fields(employee_id)
    if not fields:
        return JSONResponse({"error": "Сотрудник не найден"}, status_code=404)

    buf = generate_questionnaire(fields)
    surname = fields.get("surname", "работник")
    filename = f"anketa_{surname}.docx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
