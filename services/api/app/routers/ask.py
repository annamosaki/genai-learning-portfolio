from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..rag.pipeline import ChatTurn, answer_question

router = APIRouter(tags=["ask"])


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=40)


@router.post("/ask")
def ask(body: AskRequest):
    history = [ChatTurn(role=m.role, content=m.content) for m in body.history]
    return answer_question(body.question.strip(), history=history)
