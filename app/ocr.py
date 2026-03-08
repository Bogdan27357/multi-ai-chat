"""OCR + LLM document processing — extract structured data from document images.

Fully local pipeline using Ollama + Tesseract + EasyOCR.

Supports multiple recognition modes:
- printed: Tesseract OCR + LLM parsing (best for printed/typed text)
- handwritten: EasyOCR + Ollama vision model (best for handwritten text)
- auto: tries Ollama vision model first, falls back to combined OCR
"""

import base64
import io
import json
import os

import httpx
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OCR_MODEL = os.getenv("OCR_MODEL", "llama3.1:8b")
VISION_MODEL = os.getenv("VISION_MODEL", "llava")

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
    "handwritten": {
        "name": "Рукописный документ",
        "fields": [
            ("title", "Заголовок/тема"),
            ("author", "Автор"),
            ("date", "Дата"),
            ("content", "Содержание"),
        ],
    },
    "auto": {
        "name": "Авто-определение",
        "fields": [],
    },
}


# ---- Image preprocessing ----

def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess image for better OCR: grayscale, contrast, sharpen, binarize."""
    img = image.convert("L")

    # Resize if too small (OCR works better on larger images)
    w, h = img.size
    if w < 1000:
        scale = 1000 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Enhance contrast
    img = ImageEnhance.Contrast(img).enhance(1.8)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)

    # Adaptive-like binarization
    img = img.point(lambda x: 255 if x > 140 else 0, "1")
    img = img.convert("L")

    return img


def image_to_base64(image: Image.Image, max_size: int = 1024) -> str:
    """Convert PIL Image to base64 string, resizing if needed."""
    img = image.copy()
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ---- OCR engines ----

def extract_text_tesseract(image: Image.Image) -> str:
    """Run Tesseract OCR on a preprocessed image."""
    preprocessed = preprocess_image(image)
    text = pytesseract.image_to_string(preprocessed, lang="rus+eng")
    return text.strip()


def extract_text_easyocr(image: Image.Image) -> str:
    """Run EasyOCR on an image (better for handwritten text)."""
    try:
        import easyocr
    except ImportError:
        return ""

    import numpy as np
    img_array = np.array(image.convert("RGB"))

    reader = easyocr.Reader(["ru", "en"], gpu=False, verbose=False)
    results = reader.readtext(img_array, detail=0, paragraph=True)
    return "\n".join(results).strip()


def extract_text_from_image(image: Image.Image) -> str:
    """Run Tesseract OCR on an image with preprocessing, return extracted text."""
    return extract_text_tesseract(image)


def extract_text_combined(image: Image.Image) -> str:
    """Run both Tesseract and EasyOCR, combine results for best coverage."""
    tesseract_text = extract_text_tesseract(image)
    easyocr_text = extract_text_easyocr(image)

    if not easyocr_text:
        return tesseract_text
    if not tesseract_text:
        return easyocr_text

    # EasyOCR as primary (better for handwriting), Tesseract as supplement
    return (
        f"{easyocr_text}\n\n"
        f"--- Дополнительное распознавание ---\n{tesseract_text}"
    )


# ---- Vision LLM extraction (bypasses OCR — reads image directly) ----

def _build_fields_instruction(doc_type: str) -> str:
    """Build the fields extraction instruction for a given doc type."""
    if doc_type == "auto":
        return (
            "Определи тип документа и извлеки все поля, которые найдёшь. "
            "Верни JSON с ключом 'document_type' (тип документа) и остальными полями."
        )
    doc_info = DOCUMENT_TYPES[doc_type]
    fields_list = "\n".join(
        f'- "{code}": {label}' for code, label in doc_info["fields"]
    )
    return (
        f"Это документ: {doc_info['name']}.\n"
        f"Извлеки следующие поля:\n{fields_list}\n"
        f'Верни JSON с этими ключами. Если поле не найдено, поставь "".'
    )


async def extract_with_ollama_vision(image: Image.Image, doc_type: str) -> dict | None:
    """Send image to Ollama vision model (llava, bakllava, etc.) for direct extraction."""
    img_b64 = image_to_base64(image, max_size=1536)
    fields_instruction = _build_fields_instruction(doc_type)

    prompt = f"""Ты — система извлечения данных из документов.
Внимательно прочитай текст на изображении документа.
Документ может содержать как печатный, так и рукописный текст.
Прочитай ВСЁ, включая рукописные записи, подписи, даты.

{fields_instruction}

ВАЖНО: Верни ТОЛЬКО валидный JSON, без пояснений, без markdown."""

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": VISION_MODEL,
                    "messages": [{
                        "role": "user",
                        "content": prompt,
                        "images": [img_b64],
                    }],
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"].strip()
            return _parse_json_response(content)
    except Exception:
        return None


# ---- LLM parsing ----

def _parse_json_response(content: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [line for line in lines if not line.startswith("```")]
        content = "\n".join(lines)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"_raw_response": content, "_error": "Не удалось распарсить JSON"}


async def parse_document_with_llm(ocr_text: str, doc_type: str) -> dict:
    """Send OCR text to Ollama LLM to extract structured fields."""
    fields_instruction = _build_fields_instruction(doc_type)

    prompt = f"""Ты — система извлечения данных из документов.
Тебе дан текст, распознанный OCR с изображения документа.
OCR может содержать ошибки — постарайся исправить очевидные опечатки.
Текст может быть частично распознан из рукописного ввода — восстанови смысл.

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

    return _parse_json_response(content)


# ---- Main extraction pipeline ----

async def process_document_image(
    image: Image.Image, doc_type: str, mode: str = "auto"
) -> dict:
    """Full document processing pipeline (fully local via Ollama).

    Modes:
    - 'printed': Tesseract OCR + LLM parsing
    - 'handwritten': Ollama vision model -> EasyOCR + LLM fallback
    - 'auto': tries Ollama vision first, then falls back to OCR
    """
    ocr_text = ""
    fields = {}
    vision_used = False

    if mode in ("handwritten", "auto"):
        # Try Ollama vision model first (best for handwriting)
        vision_result = await extract_with_ollama_vision(image, doc_type)
        if vision_result and "_error" not in vision_result:
            fields = vision_result
            vision_used = True

    if mode == "handwritten" and not vision_used:
        # Fallback: combined OCR (EasyOCR primary) for handwritten
        ocr_text = extract_text_combined(image)
        if ocr_text:
            fields = await parse_document_with_llm(ocr_text, doc_type)
    elif mode == "printed" or (mode == "auto" and not vision_used):
        # Use Tesseract for printed text
        ocr_text = extract_text_tesseract(image)
        if ocr_text:
            fields = await parse_document_with_llm(ocr_text, doc_type)

    # If vision was used, also run OCR for the raw text display
    if vision_used and not ocr_text:
        ocr_text = extract_text_tesseract(image)

    return {
        "ocr_text": ocr_text,
        "fields": fields,
        "vision_used": vision_used,
    }
