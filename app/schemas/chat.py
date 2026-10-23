from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=8)


class ChatSource(BaseModel):
    title: str
    type: Literal["document", "session", "venue"]
    reference: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
