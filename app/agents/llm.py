from typing import Tuple, List
import logging
import os

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

from app.agents.base import Agent
from app.agents.knowledge import KnowledgeAgent
from app.config import LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE
from app.prompts import build_system_prompt, build_user_prompt


logger = logging.getLogger(__name__)


class LLMAgent(Agent):
    """Agent that composes RAG context and queries an external LLM service.

    Falls back to `KnowledgeAgent` when the LLM client is unavailable or on
    runtime errors. Designed to keep responses grounded by passing retrieved
    context and instructing citations/refusals via prompt templates.
    """
    def __init__(self) -> None:
        self.knowledge = KnowledgeAgent()
        self.client = None
        if OpenAI is not None and os.environ.get("OPENAI_API_KEY"):
            try:
                self.client = OpenAI()
            except Exception:  # pragma: no cover
                logger.debug("LLMAgent could not initialize OpenAI client; running in fallback mode")
                self.client = None

    async def handle(self, message: str, user_id: str) -> Tuple[str, str]:
        """Return (route, answer) using LLM with RAG context or safe fallback."""
        # Retrieve top-k chunks as context
        chunks: List[str] = self.knowledge.retrieve(message, k=5)
        # Truncate context to a safe character budget to avoid overly long prompts
        budget = 4000
        trimmed: List[str] = []
        total = 0
        for ch in chunks:
            if total + len(ch) > budget:
                break
            trimmed.append(ch)
            total += len(ch)
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(query=message, chunks=trimmed)

        if self.client is None:
            # Fallback: delegate to KnowledgeAgent to craft a concise answer
            logger.debug("LLMAgent fallback: no client; delegating to KnowledgeAgent")
            route, answer = await self.knowledge.handle(message, user_id)
            # Preserve that this came from LLM fallback for observability
            return ("llm:fallback", answer)

        try:
            chat = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
            )
            answer = chat.choices[0].message.content or ""
            return ("llm", answer)
        except Exception:
            logger.exception("LLMAgent completion error; falling back to concatenated RAG context")
            joined = "\n\n".join(trimmed) if trimmed else ""
            return ("llm:fallback", joined or "Sem contexto relevante encontrado.")


