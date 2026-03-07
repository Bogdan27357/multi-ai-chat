"""OCR + LLM document processing — extract structured data from document images."""

import json
import os

import httpx
from PIL import Image
import pytesseract


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OCR_MODEL = os.getenv("OCR_MODEL", "llama3.1:8b")

# Document types and their expected fields
DOCUMENT_TYPES = {
    "passport": {
        "name": "Паспорт РФ",
        "fields": [
            ("surname", "Фамилия"),
            ("name", "Имя"),
            ("patronymic", "Отчество"),
            ("gender", "Пол"),
            ("birth_date", "Дата рождения"),
            ("birth_place", "Место рождения"),
            ("series", "Серия паспорта"),
            ("number", "Номер паспорта"),
            ("issue_date", "Дата выдачи"),
            ("issued_by", "Кем выдан"),
            ("department_code", "Код подразделения"),
        ],
    },
    "snils": {
        "name": "СНИЛС",
        "fields": [
            ("surname", "Фамилия"),
            ("name", "Имя"),
            ("patronymic", "Отчество"),
            ("birth_date", "Дата рождения"),
            ("snils_number", "Номер СНИЛС"),
        ],
    },
    "inn": {
        "name": "ИНН",
        "fields": [
            ("surname", "Фамилия"),
            ("name", "Имя"),
            ("patronymic", "Отчество"),
            ("inn_number", "Номер ИНН"),
        ],
    },
    "diploma": {
        "name": "Диплом",
        "fields": [
            ("surname", "Фамилия"),
            ("name", "Имя"),
            ("patronymic", "Отчество"),
            ("institution", "Учебное заведение"),
            ("specialty", "Специальность"),
            ("qualification", "Квалификация"),
            ("issue_date", "Дата выдачи"),
            ("series", "Серия"),
            ("number", "Номер"),
        ],
    },
    "auto": {
        "name": "Авто-определение",
        "fields": [],
    },
}


def extract_text_from_image(image: Image.Image) -> str:
    """Run Tesseract OCR on an image, return extracted text."""
    text = pytesseract.image_to_string(image, lang="rus+eng")
    return text.strip()


async def parse_document_with_llm(ocr_text: str, doc_type: str) -> dict:
    """Send OCR text to Ollama LLM to extract structured fields."""

    if doc_type == "auto":
        fields_instruction = (
            "Определи тип документа и извлеки все поля, которые найдёшь. "
            "Верни JSON с ключом 'document_type' (тип документа) и остальными полями."
        )
    else:
        doc_info = DOCUMENT_TYPES[doc_type]
        fields_list = "\n".join(
            f'- "{code}": {label}' for code, label in doc_info["fields"]
        )
        fields_instruction = (
            f"Это документ: {doc_info['name']}.\n"
            f"Извлеки следующие поля:\n{fields_list}\n"
            f'Верни JSON с этими ключами. Если поле не найдено, поставь "".'
        )

    prompt = f"""Ты — система извлечения данных из документов.
Тебе дан текст, распознанный OCR с изображения документа.
OCR может содержать ошибки — постарайся исправить очевидные опечатки.

{fields_instruction}

ВАЖНО: Верни ТОЛЬКО валидный JSON, без пояснений, без markdown.

Распознанный текст:
---
{ocr_text}
---"""

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OCR_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]

    # Try to parse JSON from LLM response
    content = content.strip()
    # Strip markdown code block if present
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        content = "\n".join(lines)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"_raw_response": content, "_error": "Не удалось распарсить JSON"}
