# Multi-AI Chat

Веб-приложение для одновременного общения с несколькими AI-моделями. **Все провайдеры бесплатные** — локальная Ollama + бесплатные облачные API.

## Возможности

- Одновременные запросы к нескольким AI-моделям
- Сравнение ответов бок о бок
- Поддержка истории диалога
- Тёмный интерфейс
- 5 провайдеров, 15+ моделей — всё бесплатно

## Провайдеры и модели

### Локальный (офлайн)

| Провайдер | Модели | Как получить |
|-----------|--------|-------------|
| **Ollama** | llama3.1:8b, mistral:7b, gemma2:9b, qwen2.5:7b, phi3:mini | [ollama.com](https://ollama.com) — установить + `ollama pull model` |

### Облачные (бесплатные)

| Провайдер | Модели | Лимиты | Как получить ключ |
|-----------|--------|--------|-------------------|
| **Google Gemini** | gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro | 15 RPM, 1M tok/день | [aistudio.google.com](https://aistudio.google.com/) |
| **Groq** | llama-3.3-70b, mixtral-8x7b, gemma2-9b | 30 RPM, 14400 req/день | [console.groq.com](https://console.groq.com/) |
| **Cohere** | command-r-plus, command-r | 20 RPM | [dashboard.cohere.com](https://dashboard.cohere.com/) |
| **HuggingFace** | Mistral-7B-Instruct, Phi-3-mini | Rate-limited | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

## Установка

```bash
git clone https://github.com/your-username/multi-ai-chat.git
cd multi-ai-chat

python -m venv .venv
source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt

# Настроить ключи
cp .env.example .env
# Отредактируйте .env — добавьте ключи от нужных сервисов
```

### Для Ollama (опционально)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
ollama pull mistral:7b
```

## Запуск

```bash
uvicorn app.main:app --reload
```

Откройте http://localhost:8000 в браузере.

## Использование

1. Выберите одну или несколько моделей в верхней панели
2. Введите сообщение и нажмите «Отправить» (или Enter)
3. Получите ответы от всех выбранных моделей одновременно
