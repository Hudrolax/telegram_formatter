# Telegram Formatter

Лёгкий backend‑сервис, который принимает Markdown и возвращает Telegram‑совместимый HTML, аккуратно очищая неподдерживаемые символы и разбивая длинные сообщения.

## Возможности

- Конвертация Markdown → Telegram HTML
- Санитизация входного текста и HTML
- Разбиение сообщений по лимиту Telegram с сохранением блоков кода
- Простое API на FastAPI

## Запуск

```bash
docker compose up -d
```

Сервис будет доступен по адресу `http://localhost:8000`.

## Ручное тестирование

Пример запроса:

```bash
curl -X POST "http://localhost:8000/api/v1/format" \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, **мир**"}'
```

Пример ответа (Telegram HTML):

```json
[
  {
    "text": "Привет, <b>мир</b>"
  }
]
```

## Тестирование

Тесты нужно запускать в контейнере.

```bash
docker compose run --rm app sh -c "pytest"
```

## Линтинг

```bash
cd app
ruff check .
```

## Репозиторий

- Локальные окружения, кеши и артефакты сборки исключены через `.gitignore` (например, `venv/`, `build/`, `.ruff_cache/`, `.env`).
- Шаблон переменных окружения хранится в `.env-example`.

## API

- `POST /api/v1/format` — принимает `{ "text": "..." }` и возвращает массив частей сообщения.
- `GET /api/v1/healthcheck` — проверка доступности сервиса.
