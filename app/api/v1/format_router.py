from fastapi import APIRouter
from pydantic import BaseModel, Field

from config.config import settings
from domain.services.telegram_formatter import format_markdown_for_telegram


class FormatRequest(BaseModel):
    text: str = Field(..., description="Сообщение в формате Markdown")


class MessagePart(BaseModel):
    text: str


router = APIRouter(prefix="/format", tags=["formatter"])


@router.post("", response_model=list[MessagePart])
async def format_message(payload: FormatRequest) -> list[MessagePart]:
    parts = format_markdown_for_telegram(payload.text, settings.TELEGRAM_MAX_MESSAGE_LENGTH)
    return [MessagePart(text=part) for part in parts]
