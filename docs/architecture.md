# Architecture of the "Telegram Formatter" Project

## Overview

This project is a lightweight backend service that accepts Markdown text and returns Telegram-compatible HTML message parts. It focuses on sanitizing unsupported characters, formatting embedded JSON into fenced code blocks, converting Markdown to Telegram HTML (including custom emoji tags), and splitting messages to Telegram's length limit (counted after entity parsing), with careful handling of code blocks.

## Technology Stack

- **Language**: Python 3.13
- **Web Framework**: FastAPI (v0.115+)
- **Server**: Uvicorn
- **Configuration**: Pydantic Settings
- **Markdown Parser**: markdown-it-py
- **Containerization**: Docker & Docker Compose

## Project Structure

The service follows a clean-ish separation of concerns similar to the reference project.

### 1. `app/api` (Interface Layer)

Contains FastAPI routers and endpoints.

- **`v1/`**: Versioned API.
  - `healthcheck_router.py`: Liveness endpoint (e.g., `GET /api/v1/healthcheck`).
  - `format_router.py`: Formatting endpoint (e.g., `POST /api/v1/format`).

### 2. `app/domain` (Domain Layer)

Contains core business logic for message formatting.

- **`services/telegram_formatter.py`**: Sanitization, Markdown → Telegram HTML conversion, Telegram HTML sanitization, and message splitting.

### 3. `app/config`

- `config.py`: Pydantic settings for runtime configuration (e.g., `API_ROOT_PATH`, `TELEGRAM_MAX_MESSAGE_LENGTH`, `LOG_LEVEL`).
- `logger.py`: Logging configuration.

## Processing Flow

1. API accepts Markdown text.
2. Text is sanitized (control characters removed).
3. Embedded valid JSON (outside code spans/blocks) is converted into fenced code blocks with pretty formatting.
4. Markdown is converted to Telegram HTML and sanitized to allowed tags/attributes.
5. Result is split into multiple message parts if it exceeds the configured length (by Telegram's entity-parsed length), keeping code blocks intact when possible.
6. API returns an array of message objects `{ "text": "..." }`.

## Development & Deployment

- **Docker**: Two-stage build for production images.
- **Environment**: Configured via `.env` or environment variables.
