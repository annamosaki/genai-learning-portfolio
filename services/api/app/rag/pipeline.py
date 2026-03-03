"""Answer Ask Anna questions with the full CV + chat history in every prompt."""

from __future__ import annotations

import logging
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from ..config import get_settings
from .corpus import corpus_char_count, full_cv_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Ask Anna, a helpful assistant for Anna Mosaki's portfolio.

You are given Anna's full CV in this system message, plus the ongoing chat history.

Rules:
- Use only facts from the CV for questions about Anna. Do not invent employers, dates, skills, or contact details.
- If a fact is not in the CV, say you don't know from her CV.
- You DO have memory of this conversation: you can recall prior user questions and your prior answers from the chat history.
- Answer in the same language as the user when possible (default English).
- For greetings, thanks, or off-topic chat: reply briefly and warmly, then offer to answer questions about her experience, education, skills, awards, projects, or contact.
- Contact details (email, phone, location, links) may be shared when asked — they are public on the CV.
- Chronology: treat education years as chronological (earliest school first when asked what she attended first).
- Do not invent or upgrade credentials: if the CV says she studied somewhere without completing a degree, say that clearly — never imply a degree was earned there.

Formatting (important — the UI shows your newlines):
- Prefer short paragraphs and Markdown lists. Never pack multiple items into one long line.
- For education, experience, awards, skills, or projects: use a bullet list with a blank line between items when helpful.
- Example shape for education:
  Anna's education:
  - **School name** — degree or studies (years)
    Detail note if needed
  - **Next school** — …
- Use **bold** sparingly for school/company names. Do not wrap the whole answer as one paragraph.
"""

MAX_HISTORY = 20


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


def answer_question(question: str, history: list[ChatTurn] | None = None) -> dict:
    cv = full_cv_context()
    settings = get_settings()
    base = {
        "mode": "cv-context",
        "corpus_chars": corpus_char_count(),
    }

    if not settings.openai_api_key:
        return {
            **base,
            "answer": (
                "Ask Anna needs an OPENAI_API_KEY in `.env` to answer from the CV. "
                "Add a key, restart the API, then try again."
            ),
        }

    prior = list(history or [])[-MAX_HISTORY:]
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\nANNA'S CV:\n\n{cv}",
        },
    ]
    for turn in prior:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": question})

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=500,
            timeout=30.0,
            messages=messages,
        )
        answer = (completion.choices[0].message.content or "").strip()
        if not answer:
            answer = "I couldn't generate an answer. Please try again."
        return {**base, "answer": answer, "mode": "cv-context-openai"}
    except Exception as exc:
        name = type(exc).__name__
        logger.warning("OpenAI Ask failed: %s: %s", name, exc)
        if name == "RateLimitError" or "insufficient_quota" in str(exc):
            msg = (
                "OpenAI quota exceeded — Ask Anna can't call the model until billing is topped up "
                "at https://platform.openai.com/account/billing. "
                "The CV is ready in context; only the LLM call is blocked."
            )
        elif name == "AuthenticationError":
            msg = "OpenAI API key is invalid. Check OPENAI_API_KEY in `.env` and restart the API."
        else:
            msg = f"Could not reach the language model ({name}). Please try again in a moment."
        return {**base, "answer": msg, "mode": "cv-context-error"}
