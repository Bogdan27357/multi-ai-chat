# Multi-AI Chat

Веб-приложение для одновременного общения с несколькими AI-моделями. Отправляйте один запрос — получайте ответы от OpenAI, Anthropic (Claude) и Google (Gemini) рядом друг с другом.

## Возможности

- Одновременные запросы к нескольким AI-провайдерам
- Сравнение ответов разных моделей бок о бок
- Поддержка истории диалога
- Тёмный интерфейс

## Поддерживаемые провайдеры

| Провайдер | Модели |
|-----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo |
| **Anthropic** | Claude Sonnet 4, Claude Haiku 4.5, Claude 3.5 Sonnet |
| **Google** | Gemini 2.0 Flash, Gemini 1.5 Pro, Gemini 1.5 Flash |

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/your-username/multi-ai-chat.git
cd multi-ai-chat

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Установить зависимости
pip install -r requirements.txt

# Настроить API ключи
cp .env.example .env
# Отредактируйте .env и добавьте свои ключи
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
