from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class Source(BaseModel):
    source: str
    page: int | None = None
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
