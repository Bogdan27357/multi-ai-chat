# Multi-AI Chat

Веб-приложение для одновременного общения с несколькими AI-моделями через **локальную Ollama**. Полностью бесплатно и офлайн — никаких API ключей.

## Возможности

- Одновременные запросы к нескольким моделям через Ollama
- Сравнение ответов разных моделей бок о бок
- Поддержка истории диалога
- Тёмный интерфейс
- Полностью локальное — данные не уходят в облако

## Поддерживаемые модели

| Модель | Размер | Описание |
|--------|--------|----------|
| **llama3.1:8b** | ~4.7 GB | Meta Llama 3.1 — отличное качество для своего размера |
| **mistral:7b** | ~4.1 GB | Mistral 7B — быстрая и качественная |
| **gemma2:9b** | ~5.4 GB | Google Gemma 2 — хороша для диалогов |
| **qwen2.5:7b** | ~4.4 GB | Alibaba Qwen 2.5 — сильна в коде и логике |
| **phi3:mini** | ~2.3 GB | Microsoft Phi-3 Mini — компактная и быстрая |

## Установка

### 1. Установить Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS — скачать с https://ollama.com/download
# Windows — скачать с https://ollama.com/download
```

### 2. Скачать модели

```bash
# Рекомендуемый минимум (выберите 2-3):
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull gemma2:9b

# Дополнительные:
ollama pull qwen2.5:7b
ollama pull phi3:mini
```

### 3. Установить приложение

```bash
git clone https://github.com/your-username/multi-ai-chat.git
cd multi-ai-chat

python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

## Запуск

```bash
# Убедитесь что Ollama запущена:
ollama serve

# В другом терминале:
uvicorn app.main:app --reload
```

Откройте http://localhost:8000 в браузере.

## Использование

1. Выберите одну или несколько моделей в верхней панели
2. Введите сообщение и нажмите «Отправить» (или Enter)
3. Получите ответы от всех выбранных моделей одновременно
